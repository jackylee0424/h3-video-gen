"""Command line: python -m h3gen {check,generate,example} ...

Progress goes to stderr; the final result is one JSON object on stdout (agent-friendly).
"""

import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import time

from . import graph as G
from .comfy import Comfy, ComfyError, execution_seconds, output_files

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(REPO, 'samples', 'examples.json')
REQUIRED_NODES = ('UNETLoader', 'CLIPLoader', 'VAELoader', 'Load LakonLab Adapter', 'MiniMaxH3SigmaShift',
                  'BlockSparseAttention', 'MiniMaxH3ImageToVideo', 'pi-Flow Scheduler', 'SamplerCustomAdvanced',
                  'DWD Decode', 'VAEDecodeAudio', 'CreateVideo', 'SaveVideo')


def log(*a):
    print('[h3gen]', *a, file=sys.stderr, flush=True)


def default_url():
    return os.environ.get('H3_URL') or f"http://{os.environ.get('H3_HOST', '127.0.0.1')}:{os.environ.get('H3_PORT', '8190')}"


def slug(text, n=40):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:n] or 'video'


# --- model resolution --------------------------------------------------------------------------------------------
def resolve_models(c: Comfy, args) -> dict:
    """Pick model files that ComfyUI can actually see; fail early with a fix-it hint."""
    unets = c.choices('UNETLoader', 'unet_name')
    clips = c.choices('CLIPLoader', 'clip_name')
    vaes = c.choices('VAELoader', 'vae_name')
    loras = c.choices('Load LakonLab Adapter', 'adapter_name')
    problems = []

    def need(name, avail, what, hint):
        if name not in avail:
            problems.append(f'{what} {name!r} not found ({hint})')
        return name

    m = {}
    m['unet'] = need(args.unet or G.UNET, unets, 'transformer', 'bash scripts/download_models.sh')
    m['clip'] = need(args.clip or G.CLIP, clips, 'text encoder', 'bash scripts/download_models.sh')
    m['audio_vae'] = need(G.AUDIO_VAE, vaes, 'audio VAE', 'bash scripts/download_models.sh')
    if args.video_vae:
        m['video_vae'] = need(args.video_vae, vaes, 'video VAE', 'check the name')
    else:
        m['video_vae'] = next((v for v in G.VIDEO_VAE_PREFERENCE if v in vaes), None)
        if not m['video_vae']:
            problems.append('no MiniMax H3 video VAE found (bash scripts/download_models.sh)')
    hint = 'bash scripts/download_models.sh --profile full' if args.steps == 4 else 'bash scripts/download_models.sh'
    m['adapter'] = need(args.adapter or G.ADAPTERS[args.steps], loras, f'{args.steps}-step adapter', hint)
    if problems:
        raise ComfyError('; '.join(problems))
    return m


def spark_nodes(info: dict) -> list[str]:
    """Spark-Attn node classes ComfyUI registered (one per GPU arch the installed package was built for)."""
    return sorted(n for n in info if n.startswith(G.SPARK_NODE_PREFIX))


def resolve_spark_node(c: Comfy) -> str:
    nodes = spark_nodes(c.object_info())
    if not nodes:
        raise ComfyError('Spark-Attn node not registered (install it: bash scripts/setup.sh --spark, then restart '
                         'the server)')
    if len(nodes) > 1:
        raise ComfyError(f'several Spark-Attn nodes registered: {nodes}; expected one per GPU architecture')
    return nodes[0]


# --- commands ----------------------------------------------------------------------------------------------------
def cmd_check(args):
    c = Comfy(args.url)
    report = {'url': args.url, 'server': c.alive()}
    if not report['server']:
        report['hint'] = 'start the server: bash scripts/serve.sh'
        print(json.dumps(report, indent=1))
        return 1
    stats = c.system_stats()
    report['comfyui'] = stats.get('system', {}).get('comfyui_version')
    report['devices'] = [{'name': d.get('name'), 'vram_total_gb': round(d.get('vram_total', 0) / 2**30, 1),
                          'vram_free_gb': round(d.get('vram_free', 0) / 2**30, 1)} for d in stats.get('devices', [])]
    info = c.object_info()
    report['missing_nodes'] = [n for n in REQUIRED_NODES if n not in info]
    report['spark_attention'] = spark_nodes(info) or 'not installed (optional: bash scripts/setup.sh --spark)'
    for steps in (2, 4):
        args.steps = steps
        try:
            report[f'models_{steps}step'] = resolve_models(c, args)
        except ComfyError as e:
            report[f'models_{steps}step'] = f'MISSING: {e}'
    report['ready'] = not report['missing_nodes'] and isinstance(report['models_2step'], dict)
    print(json.dumps(report, indent=1))
    return 0 if report['ready'] else 1


def run_generation(c: Comfy, *, prompt, first=None, last=None, steps=2, seconds=5.0, aspect='16:9', megapixels=1.0,
                   width=None, height=None, seed=None, out=None, label=None, args=None, dry_run=False):
    if width or height:
        if not (width and height):
            raise SystemExit('--width and --height go together')
        if width % 32 or height % 32:
            raise SystemExit('width and height must be multiples of 32')
    else:
        width, height = G.canvas_size(aspect, megapixels)
    frames = G.frame_count(seconds)
    seed = random.randrange(2**31) if seed is None else seed
    for p in (first, last):
        if p and not os.path.isfile(p):
            raise SystemExit(f'image not found: {p}')

    args.steps = steps
    online = not dry_run or c.alive()
    models = resolve_models(c, args) if online else {
        'unet': G.UNET, 'clip': G.CLIP, 'video_vae': G.VIDEO_VAE_PREFERENCE[0], 'audio_vae': G.AUDIO_VAE,
        'adapter': G.ADAPTERS[steps]}
    attention = 'dense' if args.dense else args.attention
    if attention == 'auto':  # Spark-Attn when its node is installed (closest to dense), else built-in Sol
        attention = 'spark' if online and spark_nodes(c.object_info()) else 'sol'
    spark_node = (resolve_spark_node(c) if online else G.SPARK_NODE_PREFIX + '120') if attention == 'spark' else None
    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    name = f'{stamp}_{slug(label or prompt)}_s{seed}_{steps}step' + ('' if attention == 'sol' else f'_{attention}')
    out = out or os.path.join(REPO, 'outputs', name + '.mp4')

    first_name = c.upload_image(first) if first and not dry_run else (os.path.basename(first) if first else None)
    last_name = c.upload_image(last) if last and not dry_run else (os.path.basename(last) if last else None)
    g = G.build_graph(prompt=prompt, width=width, height=height, frames=frames, steps=steps, seed=seed,
                      first_image=first_name, last_image=last_name, attention=attention, sol_tau=args.sol_tau,
                      **({'spark_node': spark_node} if spark_node else {}), filename_prefix=f'h3gen/{name}',
                      **models)
    settings = dict(label=label, prompt=prompt, first_frame=first, last_frame=last, steps=steps, seed=seed,
                    seconds_requested=seconds, num_frames=frames, duration_s=round(frames / G.FPS, 3), fps=G.FPS,
                    width=width, height=height, aspect_ratio=None if args.width else aspect,
                    megapixels=None if args.width else megapixels, attention=attention,
                    sol_tau=args.sol_tau if attention == 'sol' else None,
                    sol_extra_tokens=G.SOL_SETTINGS['extra_tokens'] if attention == 'sol' else None,
                    spark_node=spark_node, spark_mode=G.SPARK_SETTINGS['mode'] if spark_node else None,
                    models=models)
    if dry_run:
        print(json.dumps({'settings': settings, 'graph': g}, indent=1))
        return 0

    log(f'{width}x{height}, {frames} frames ({frames / G.FPS:.2f}s), {steps} steps, seed {seed}'
        + (f', first={os.path.basename(first)}' if first else '') + (f', last={os.path.basename(last)}' if last else ''))
    t0 = time.time()
    pid = c.queue(g)
    log(f'queued {pid}')
    last_tick = [0.0]

    def tick(elapsed):
        if elapsed - last_tick[0] >= 15:
            last_tick[0] = elapsed
            log(f'... {elapsed:.0f}s')

    entry = c.wait(pid, timeout=args.timeout, on_tick=tick)
    wall = time.time() - t0
    files = [f for f in output_files(entry) if f['filename'].endswith(('.mp4', '.webm', '.mkv', '.mov'))]
    if not files:
        raise ComfyError('finished but produced no video: ' + json.dumps(entry.get('outputs'))[:2000])
    c.download(files[0], out)
    result = dict(output=os.path.abspath(out), prompt_id=pid, wall_seconds=round(wall, 2),
                  execution_seconds=execution_seconds(entry), settings=settings,
                  comfyui_file=files[0], created=dt.datetime.now().isoformat(timespec='seconds'))
    with open(os.path.splitext(out)[0] + '.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    log(f'done in {wall:.1f}s -> {out}')
    return result


def read_prompt(args):
    if args.prompt_file:
        with open(args.prompt_file, encoding='utf-8') as f:
            return f.read().strip()
    if args.prompt:
        return args.prompt
    raise SystemExit('give --prompt or --prompt-file')


def cmd_generate(args):
    c = Comfy(args.url)
    res = run_generation(c, prompt=read_prompt(args), first=args.first, last=args.last, steps=args.steps,
                         seconds=args.seconds, aspect=args.aspect, megapixels=args.megapixels, width=args.width,
                         height=args.height, seed=args.seed, out=args.out, label=args.label, args=args,
                         dry_run=args.dry_run)
    if isinstance(res, dict):
        print(json.dumps(res, ensure_ascii=False))
    return 0


def load_examples():
    with open(EXAMPLES, encoding='utf-8') as f:
        return json.load(f)


def cmd_example(args):
    examples = load_examples()
    if args.list or not (args.names or args.all):
        for e in examples:
            print(f"{e['id']:24s} {e['label']}  ({e['duration']}s, {e['aspect_ratio']}, "
                  f"first={'y' if e['in_image'] else 'n'} last={'y' if e['in_last_image'] else 'n'})")
        return 0
    chosen = examples if args.all else [e for e in examples if e['id'] in args.names]
    unknown = set(args.names or []) - {e['id'] for e in examples}
    if unknown:
        raise SystemExit(f'unknown example(s): {sorted(unknown)}; see: python -m h3gen example --list')
    c = Comfy(args.url)
    rc = 0
    for e in chosen:
        img = lambda p: os.path.join(REPO, p) if p else None  # noqa: E731
        for p in (e['in_image'], e['in_last_image']):
            if p and not os.path.isfile(img(p)):
                raise SystemExit(f'missing sample image {p}: run bash scripts/fetch_samples.sh')
        try:
            res = run_generation(
                c, prompt=e['prompt'], first=img(e['in_image']), last=img(e['in_last_image']),
                steps=args.steps or e['steps'], seconds=args.seconds or e['duration'], aspect=e['aspect_ratio'],
                megapixels=args.megapixels or e['megapixels'], seed=e['seed'] if args.seed is None else args.seed,
                label=e['id'], args=args, dry_run=args.dry_run)
            if isinstance(res, dict):
                print(json.dumps(res, ensure_ascii=False), flush=True)
        except ComfyError as err:
            log(f"{e['id']} FAILED: {err}")
            rc = 1
    return rc


def main(argv=None):
    p = argparse.ArgumentParser(prog='h3gen', description='pi-H3 video generation through a local ComfyUI')
    p.add_argument('--url', default=default_url(), help='ComfyUI base URL (env H3_URL; default %(default)s)')
    sub = p.add_subparsers(dest='cmd', required=True)

    def common(sp):
        sp.add_argument('--attention', choices=('auto',) + G.ATTENTIONS, default='auto',
                        help='auto (default): spark if installed, else sol. sol: built-in Sol. spark: Spark-Attn '
                             '(needs setup.sh --spark). dense: no sparse attention')
        sp.add_argument('--dense', action='store_true', help='same as --attention dense')
        sp.add_argument('--sol-tau', type=float, default=1.0, help='Sol sparsity threshold (upstream default 1.0)')
        sp.add_argument('--unet', help=f'transformer file (default {G.UNET})')
        sp.add_argument('--clip', help=f'text encoder file (default {G.CLIP})')
        sp.add_argument('--video-vae', help='video VAE file (default: int8_convrot, else fp16)')
        sp.add_argument('--adapter', help='pi-H3 adapter file (default: by --steps)')
        sp.add_argument('--timeout', type=float, default=3600)
        sp.add_argument('--dry-run', action='store_true', help='print settings + API graph, do not queue')
        sp.add_argument('--width', type=int)
        sp.add_argument('--height', type=int)

    sp = sub.add_parser('check', help='server, nodes and models ready?')
    sp.set_defaults(func=cmd_check, unet=None, clip=None, video_vae=None, adapter=None)

    sp = sub.add_parser('generate', help='generate one video')
    sp.add_argument('--prompt')
    sp.add_argument('--prompt-file')
    sp.add_argument('--first', help='first-frame reference image')
    sp.add_argument('--last', help='last-frame reference image')
    sp.add_argument('--steps', type=int, choices=(2, 4), default=2)
    sp.add_argument('--seconds', type=float, default=5.0, help='5.2..14.4 s (rounded to 17n+5 frames at 24 fps)')
    sp.add_argument('--aspect', choices=G.ASPECT_RATIOS, default='16:9')
    sp.add_argument('--megapixels', type=float, default=1.0, help='0.25..1.0 (1.0 = 1344x768 at 16:9)')
    sp.add_argument('--seed', type=int)
    sp.add_argument('--label', help='short name used in the output filename')
    sp.add_argument('--out', help='output .mp4 path (default outputs/<stamp>_<label>.mp4)')
    common(sp)
    sp.set_defaults(func=cmd_generate)

    sp = sub.add_parser('example', help='run the bundled Space examples (samples/examples.json)')
    sp.add_argument('names', nargs='*')
    sp.add_argument('--all', action='store_true')
    sp.add_argument('--list', action='store_true')
    sp.add_argument('--steps', type=int, choices=(2, 4))
    sp.add_argument('--seconds', type=float)
    sp.add_argument('--megapixels', type=float)
    sp.add_argument('--seed', type=int)
    common(sp)
    sp.set_defaults(func=cmd_example)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except ComfyError as e:
        log(f'ERROR: {e}')
        return 2
