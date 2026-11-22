"""Build the ComfyUI API-format graph for pi-H3 DWD generation.

This is a flattened, headless equivalent of upstream ComfyUI-piFlow `workflows/pi-H3-DWD.json` (v1.4.0): the
"pi-H3 Adapter" and "Frame Count" subgraphs are computed here in Python instead of with math nodes, and the
resolution/frame rules follow the official Space (`app.py`: canvas_size and num_frames).
"""

import math

FPS = 24
ASPECT_RATIOS = ('21:9', '16:9', '4:3', '1:1', '3:4', '9:16')

# Default model files (ComfyUI names, resolved through extra_model_paths.yaml). Override on the CLI.
UNET = 'minimax_h3_fl2va_pruned_int8_convrot.safetensors'
CLIP = 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'
AUDIO_VAE = 'minimax_h3_audio_vae_fp32.safetensors'
VIDEO_VAE_PREFERENCE = ('minimax_h3_video_vae_int8_convrot.safetensors', 'minimax_h3_video_vae_fp16.safetensors')
ADAPTERS = {
    2: 'pi_h3_2step_dwd_adapter_int8_convrot.safetensors',
    4: 'pi_h3_4step_dwd_adapter_int8_convrot.safetensors',
}
# pi-Flow scheduler settings per step count (upstream: max_raw_t 0.93 / 0.96, final_step_size_scale 0.6)
MAX_RAW_T = {2: 0.93, 4: 0.96}
FINAL_STEP_SIZE_SCALE = 0.6
SHIFT_VIDEO, SHIFT_AUDIO = 12.0, 3.0


def canvas_size(aspect_ratio: str, megapixels: float, multiple: int = 32) -> tuple[int, int]:
    """(width, height) for an aspect ratio at a pixel budget, rounded up to `multiple` (1 MP 16:9 -> 1344x768)."""
    aw, ah = map(float, aspect_ratio.split(':'))
    num_pixels = megapixels * 1e6
    height = (num_pixels * ah / aw) ** 0.5
    width = (num_pixels * aw / ah) ** 0.5
    return math.ceil(width / multiple) * multiple, math.ceil(height / multiple) * multiple


def frame_count(seconds: float) -> int:
    """H3 generates 17n + 5 frames at 24 fps; the Space clamps n to 7..20 (124 frames / 5.2 s .. 345 / 14.4 s)."""
    n = min(max(round((seconds * FPS - 5) / 17), 7), 20)
    return n * 17 + 5


def build_graph(
        *, prompt: str, width: int, height: int, frames: int, steps: int, seed: int,
        first_image: str | None = None, last_image: str | None = None,
        unet: str = UNET, clip: str = CLIP, video_vae: str = VIDEO_VAE_PREFERENCE[0], audio_vae: str = AUDIO_VAE,
        adapter: str | None = None, adapter_strength: float = 1.0,
        sparse_attention: bool = True, sol_tau: float = 1.0,
        filename_prefix: str = 'h3gen/pi-H3-DWD') -> dict:
    """Return a ComfyUI /prompt graph. `first_image`/`last_image` are names already uploaded to ComfyUI's input dir."""
    if steps not in ADAPTERS:
        raise ValueError('steps must be 2 or 4')
    adapter = adapter or ADAPTERS[steps]
    g: dict[str, dict] = {}

    def node(nid, cls, **inputs):
        g[str(nid)] = {'class_type': cls, 'inputs': inputs}
        return [str(nid), 0]

    # model chain: base -> pi-H3 adapter -> sigma shift -> (Sol sparse attention)
    model = node(1, 'UNETLoader', unet_name=unet, weight_dtype='default')
    model = node(2, 'Load LakonLab Adapter', model=model, adapter_name=adapter, adapter_strength=adapter_strength)
    model = node(3, 'MiniMaxH3SigmaShift', model=model, shift_video=SHIFT_VIDEO, shift_audio=SHIFT_AUDIO)
    if sparse_attention:
        model = node(4, 'BlockSparseAttention', model=model, **{
            'selection': 'sol-attn', 'selection.tau': sol_tau, 'start_percent': 0.0, 'end_percent': 1.0,
            'dense_blocks': '0, 1', 'min_tokens': 12288, 'extra_tokens': 256,
            'sink_conditioning': 'exact_kv_and_rows', 'verbose': False})

    clip_ref = node(10, 'CLIPLoader', clip_name=clip, type='minimax', device='default')
    vae_ref = node(11, 'VAELoader', vae_name=video_vae)
    audio_vae_ref = node(12, 'VAELoader', vae_name=audio_vae)

    # keyframes: center-crop + Lanczos resize onto the canvas (same as the Space's ImageOps.fit)
    cond_inputs = {}
    if first_image:
        img = node(20, 'LoadImage', image=first_image)
        cond_inputs['first_frame'] = node(21, 'ImageScale', image=img, upscale_method='lanczos',
                                          width=width, height=height, crop='center')
    if last_image:
        img = node(22, 'LoadImage', image=last_image)
        cond_inputs['last_frame'] = node(23, 'ImageScale', image=img, upscale_method='lanczos',
                                         width=width, height=height, crop='center')

    node(30, 'MiniMaxH3ImageToVideo', clip=clip_ref, vae=vae_ref, prompt=prompt,
         width=width, height=height, length=frames, **cond_inputs)
    cond, latent = ['30', 0], ['30', 1]

    noise = node(40, 'RandomNoise', noise_seed=seed)
    guider = node(41, 'BasicGuider', model=model, conditioning=cond)
    sampler = node(42, 'KSamplerSelect', sampler_name='euler')
    sigmas = node(43, 'pi-Flow Scheduler', model=model, steps=steps, min_raw_t=0.0,
                  max_raw_t=MAX_RAW_T[steps], final_step_size_scale=FINAL_STEP_SIZE_SCALE)
    samples = node(44, 'SamplerCustomAdvanced', noise=noise, guider=guider, sampler=sampler,
                   sigmas=sigmas, latent_image=latent)

    images = node(50, 'DWD Decode', samples=samples)          # pixels straight from the DWD head, no VAE decode
    audio = node(51, 'VAEDecodeAudio', samples=samples, vae=audio_vae_ref)
    video = node(52, 'CreateVideo', images=images, audio=audio, fps=float(FPS), bit_depth='auto',
                 color_space='sRGB', chroma_subsampling='auto', codec='none')
    node(53, 'SaveVideo', video=video, filename_prefix=filename_prefix, format='mp4', **{'format.codec': 'h264'})
    return g
