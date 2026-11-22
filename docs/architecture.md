# Architecture

```
Windows PowerShell                WSL2 distro (Ubuntu 24.04)                                  GPU (RTX 5090, sm_120)
------------------                ---------------------------------------------------------   ----------------------
scripts\wsl.ps1  --wsl.exe-->     scripts/*.sh   (setup / download / serve / stop / status)
                                  scripts/h3gen -> python3 -m h3gen  --HTTP :8190-->  ComfyUI v0.46.2  --> CUDA 13 / torch cu130
                                                                                      + ComfyUI-piFlow v1.4.0
repo: C:\...\h3-video-gen  ==  /mnt/c/.../h3-video-gen       runtime: ~/h3-video-gen-runtime (ComfyUI, .venv, models, logs)
outputs\*.mp4 + *.json  <-- h3gen downloads results via /view                    shared read-only: $H3_SHARED_MODELS (optional)
```

- **h3gen** (stdlib only) never imports torch. It talks to ComfyUI's HTTP API: `/upload/image`, `/prompt`,
  `/history/{id}` and `/view`. It also runs from Windows Python as long as `127.0.0.1:8190` is reachable through
  WSL localhost forwarding.
- **ComfyUI** stays running between jobs, so the models stay loaded and warm runs skip loading. It manages
  VRAM with dynamic loading and offloads weights to system RAM when needed.
- **Models** are found through `extra_model_paths.yaml`, which `setup.sh` generates. The runtime's `models/`
  folder is searched first, then `H3_SHARED_MODELS`.

## The pi-H3 DWD graph ([h3gen/graph.py](../h3gen/graph.py))

This is the flattened equivalent of upstream `ComfyUI-piFlow/workflows/pi-H3-DWD.json`:

```
UNETLoader(minimax_h3_fl2va_pruned_int8_convrot)
  -> Load LakonLab Adapter(pi_h3_{2,4}step_dwd_adapter_int8_convrot)   # pi-Flow v2 LoRA + DWD pixel head
  -> MiniMaxH3SigmaShift(video 12, audio 3)
  -> BlockSparseAttention(sol-attn, tau 1.0, dense blocks "0, 1")       # --dense skips this
CLIPLoader(qwen3vl_32b nvfp4, type minimax) + VAELoader(video VAE) + LoadImage/ImageScale(lanczos, center crop)
  -> MiniMaxH3ImageToVideo(prompt, W, H, frames, first_frame?, last_frame?)  -> CONDITIONING, LATENT
RandomNoise(seed), BasicGuider, KSamplerSelect(euler), pi-Flow Scheduler(steps, max_raw_t 0.93|0.96, final 0.6)
  -> SamplerCustomAdvanced
  -> DWD Decode   (pixels from the adapter's head at the last step; the video VAE decoder is never run)
  -> VAEDecodeAudio(audio VAE)
  -> CreateVideo(24 fps) -> SaveVideo(mp4/h264)
```

Rules copied from the official Space (`app.py`):

- canvas = aspect ratio at `megapixels * 1e6` pixels, each side rounded **up** to a multiple of 32
  (16:9 at 1 MP gives 1344x768).
- frames = `17n + 5` with `n = clamp(round((seconds*24 - 5)/17), 7, 20)`, which gives 124 frames (5.17 s) up to
  345 frames (14.4 s).
- Keyframes are center-cropped and Lanczos-resized to the canvas.
- 2 steps uses `max_raw_t` 0.93 and 4 steps uses 0.96; `final_step_size_scale` is 0.6; shift is 12 for video and
  3 for audio.

## Why ComfyUI and not the Space's own code?

The Space runs LakonLab's diffusers pipeline. It loads `multimodalart/MiniMax-H3-Pruned` in bf16 (a 133 GB repo:
about 40 GB of transformer, about 55 GB of Qwen3-VL text encoder, plus a duplicate `transformer_ref`) and
quantizes it to FP8 at load time on a ZeroGPU "xlarge" machine. Locally that means about 133 GB of downloads and
more than 54 GB of RAM just to stage the bf16 weights. The authors' ComfyUI path uses pre-quantized INT8 ConvRot / NVFP4 files and is
benchmarked by them on a 24 GB RTX 3090. See
[research/deployment-options.md](../research/deployment-options.md).
