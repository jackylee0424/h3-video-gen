# h3-video-gen

Local video + audio generation from reference images with **pi-H3** (MiniMax H3 distilled to 2–4 steps, with
DWD, *Decoding Without a Decoder*), on a single consumer NVIDIA GPU (RTX 5090 tested; RTX 4080 notes in
[docs/hardware.md](docs/hardware.md)). This is a headless, scriptable version of the
[pi-H3 Space](https://huggingface.co/spaces/Lakonik/pi-H3).

- **Engine:** ComfyUI + [ComfyUI-piFlow](https://github.com/Lakonik/ComfyUI-piFlow), running in WSL2.
  The authors' INT8 ConvRot path fits in 24–32 GB of VRAM.
- **Driver:** `h3gen`, a stdlib-only Python CLI. It builds the pi-H3 DWD graph, uploads the keyframes, runs the
  job and saves an `.mp4` file with a `.json` sidecar.
- **Inputs:** text prompt, plus an optional first-frame and/or last-frame reference image.
- **Output:** 24 fps H.264 mp4 with synchronized audio, 5–14 s long, up to 1344x768.

> **Agents:** start with [AGENTS.md](AGENTS.md).

## Quick start (from Windows PowerShell)

```powershell
git clone https://github.com/jackylee0424/h3-video-gen.git
cd h3-video-gen
.\scripts\wsl.ps1 setup            # ComfyUI v0.46.2 + ComfyUI-piFlow v1.4.2 in a uv venv (~7 GB); add --spark for Spark-Attn
.\scripts\wsl.ps1 download_models  # model files, "minimal" profile (see Disk requirements)
.\scripts\wsl.ps1 fetch_samples    # the Space's example reference images -> samples/images/
.\scripts\wsl.ps1 serve            # headless ComfyUI on 127.0.0.1:8190
.\scripts\wsl.ps1 h3gen check      # server, nodes, models ready?
.\scripts\wsl.ps1 h3gen example distracted-boyfriend
```

Your own image:

```powershell
.\scripts\wsl.ps1 h3gen generate --first C:\pics\me.png --prompt-file C:\pics\prompt.txt --seconds 5 --steps 2 --seed 42
```

Inside WSL, run the same commands as `bash scripts/<name>.sh` and `scripts/h3gen ...`. Videos go to `outputs/`.
Stop the server with `.\scripts\wsl.ps1 stop` to free the GPU. Prompts have a specific structure; see
[docs/prompting.md](docs/prompting.md).

## Speed and quality (RTX 5090)

A 5 s clip (124 frames) at 1344x768 (768p), 2 steps, with the server warm. Measured 2026-11-25 with the
`distracted-boyfriend` preset:

| `--attention` | Sampling per step | Total, prompt already encoded | Sharpness vs dense | PSNR vs dense |
|---|---:|---:|---:|---:|
| `dense` | 15.1 s | – | 100% | – |
| `sol` (built-in) | 6.45 s | 14.8 s | 67% | 14.7 dB |
| `spark` (needs `setup --spark`) | 6.76 s | 14.9 s | 98% | 18.1 dB |

The default, `--attention auto`, uses Spark when it is installed and Sol otherwise. The first render after
`serve` takes about 40 s because it loads every model from disk. Details and RTX 4080 guidance:
[docs/hardware.md](docs/hardware.md).

## Disk requirements

Every model is in ComfyUI format (INT8 ConvRot / NVFP4). Sizes are the actual file sizes on Hugging Face:

| File | Size | Profile |
|---|---:|---|
| `diffusion_models/minimax_h3_fl2va_pruned_int8_convrot` (transformer) | 21.0 GB | minimal |
| `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq` (Qwen3-VL 32B) | 15.7 GB | minimal |
| `vae/minimax_h3_video_vae_int8_convrot` (encodes keyframes only) | 2.8 GB | minimal |
| `vae/minimax_h3_audio_vae_fp32` | 0.6 GB | minimal |
| `loras/pi_h3_2step_dwd_adapter_int8_convrot` | 2.2 GB | minimal |
| `loras/pi_h3_4step_dwd_adapter_int8_convrot` | 2.2 GB | full |
| **Models, `minimal` (default)** | **≈ 42.3 GB** | |
| **Models, `full`** | **≈ 44.5 GB** | |
| Runtime: ComfyUI + venv (torch cu130) | ≈ 7 GB | |
| uv download cache (can be cleared with `uv cache prune`) | up to ≈ 7 GB | |

A fresh machine needs about **49 GB** with `minimal` and about **51 GB** with `full`, plus the uv cache until you
clear it.

```powershell
.\scripts\wsl.ps1 download_models                  # minimal: 2-step adapter only
.\scripts\wsl.ps1 download_models --profile full   # adds the 4-step adapter
.\scripts\wsl.ps1 download_models --dry-run        # show what would be fetched
```

**Reusing an existing model folder.** `H3_SHARED_MODELS` (off by default; set it in `config/h3gen.env`) is searched read-only,
and any file found there is never downloaded again. If an fp16 video VAE (`minimax_h3_video_vae_fp16`, 5.2 GB) is
already present, it is accepted in place of the int8 one. On the dev machine this left only about 7 GB of new
model downloads.

**Ways to cut disk further:**

| Option | Saves | Trade-off |
|---|---:|---|
| `minimal` profile (default): skip the 4-step adapter | 2.2 GB | 2 steps only. That's the Space default; 4 steps adds detail on complex scenes |
| Reuse an existing fp16 video VAE | 2.8 GB of downloads | Only helps if the fp16 file is already on disk; it is bigger than int8 |
| `uv cache prune` after setup | up to 7 GB | Reinstalling the venv downloads the wheels again |
| `minimax_h3_fl2va_pruned_w6a8` transformer (16.0 GB) instead of int8 ConvRot | 5 GB | **Untested** with the pi-H3 adapters; see [docs/models.md](docs/models.md) |
| ~~LakonLab/diffusers path (what the Space runs)~~ | – | Needs about 133 GB of bf16 weights and more than 54 GB of RAM. Not used here |

The text encoder is already at its smallest (nvfp4 is 15.7 GB; int8 is 27 GB and bf16 is 51 GB).

## Repo map

| Path | What |
|---|---|
| [AGENTS.md](AGENTS.md) | Operating manual for AI agents (read first) |
| [h3gen/](h3gen/) | CLI + ComfyUI API client + graph builder (stdlib only) |
| [scripts/](scripts/) | setup, download_models, fetch_samples, serve, stop, status, `h3gen`, `wsl.ps1` |
| [tools/](tools/) | `contact_sheet.py`: frame grid + stream/audio stats for checking a result without a player |
| [samples/](samples/) | `examples.json` (the Space's 3 presets); images fetched into `samples/images/` |
| [docs/](docs/) | architecture, setup, usage, prompting, models, hardware, troubleshooting |
| [research/](research/) | background on pi-H3 / DWD / MiniMax H3 and the deployment options considered |
| [work-notes/](work-notes/) | dated lab notebook: what was tried, what happened, timings |
| [config/](config/) | `h3gen.env.example` (copy to `h3gen.env` for local overrides) |

## Licenses

The code in this repo is MIT ([LICENSE](LICENSE)). The pi-H3 adapters and MiniMax H3 weights are covered by the
[MiniMax H3 Community License Agreement](https://huggingface.co/Lakonik/pi-H3/blob/main/LICENSE.md). ComfyUI-piFlow
is Apache-2.0. The sample images belong to their owners; they are fetched at runtime and not redistributed.
