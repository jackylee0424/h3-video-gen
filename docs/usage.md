# Usage: `h3gen`

Run it as `scripts/h3gen ...` in WSL, `.\scripts\wsl.ps1 h3gen ...` from PowerShell, or
`python -m h3gen ...` from the repo root with any Python 3.10+. The server must be up (`scripts/serve.sh`).

## Commands

### `check`
Prints a JSON readiness report: server, ComfyUI version, VRAM, missing nodes, and the model files resolved for
2 and 4 steps. Exits 0 when 2-step generation is possible.

### `generate`
```
scripts/h3gen generate (--prompt TEXT | --prompt-file FILE) [--first IMG] [--last IMG]
    [--steps 2|4] [--seconds 5] [--aspect 16:9] [--megapixels 1.0] [--width W --height H]
    [--seed N] [--label NAME] [--out PATH.mp4] [--attention auto|sol|spark|dense] [--sol-tau 1.0]
    [--unet F] [--clip F] [--video-vae F] [--adapter F] [--timeout 3600] [--dry-run]
```

| Flag | Default | Notes |
|---|---|---|
| `--first` / `--last` | none | Reference keyframes, center-cropped to the canvas. Both are optional, so text-only works too |
| `--steps` | 2 | 4 steps needs the `full` model profile |
| `--seconds` | 5 | Rounded to 17n+5 frames, clamped to 5.2–14.4 s |
| `--aspect` | 16:9 | 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 |
| `--megapixels` | 1.0 | 1.0 gives 1344x768 (16:9); 0.25–0.5 is much faster for drafts |
| `--width/--height` | – | Explicit canvas, multiples of 32; overrides aspect/megapixels |
| `--seed` | random | Recorded in the sidecar |
| `--attention` | `auto` | `auto`: `spark` if its node is installed, else `sol`. `sol`: ComfyUI's built-in Sol. `spark`: Spark-Attn, needs `setup.sh --spark`; closest to dense at the same speed as Sol. `dense`: no sparse attention (about 2.3x slower per step; use it to rule out sparse attention when debugging). `--dense` is the same as `--attention dense`. The sidecar records which one ran |
| `--dry-run` | off | Prints settings and the API graph; uploads and queues nothing |

### `example`
```
scripts/h3gen example --list
scripts/h3gen example distracted-boyfriend [woman-yelling-at-cat ...] | --all
    [--steps N] [--seconds S] [--megapixels M] [--seed N]
```
Runs the Space's presets from [samples/examples.json](../samples/examples.json) with their original seeds.
Run `bash scripts/fetch_samples.sh` first.

## Outputs

`outputs/<YYYYmmdd-HHMMSS>_<label>_s<seed>_<steps>step[_spark|_dense].mp4` is 24 fps H.264 video with stereo AAC audio at
32 kHz. Next to it, a `.json` sidecar holds the same object that is printed to stdout:

```json
{"output": ".../outputs/....mp4", "prompt_id": "...", "wall_seconds": 38.8, "execution_seconds": 37.7,
 "settings": {"prompt": "...", "first_frame": "...", "steps": 2, "seed": 1262275999, "num_frames": 124,
              "width": 1344, "height": 768, "attention": "sol", "models": {"unet": "...", "adapter": "..."}},
 "comfyui_file": {"filename": "..._00001_.mp4", "subfolder": "h3gen", "type": "output"}}
```

ComfyUI keeps its own copy in `~/h3-video-gen-runtime/output/h3gen/`.

To eyeball a result without a video player, build a contact sheet (8 frames plus stream and audio stats):

```bash
~/h3-video-gen-runtime/ComfyUI/.venv/bin/python tools/contact_sheet.py outputs/<file>.mp4   # -> <file>_sheet.png
```

## Batch use

Each call is independent. ComfyUI queues jobs and runs them one at a time, so loop in a shell and check each
JSON line:

```bash
for s in 1 2 3; do scripts/h3gen generate --first my.png --prompt-file p.txt --seed $s --label take$s; done
```
