# Models

All files are ComfyUI-format, resolved through `extra_model_paths.yaml`. Sources:
[Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3) (base model, text encoder, VAEs) and
[Lakonik/pi-H3](https://huggingface.co/Lakonik/pi-H3) (adapters). License:
[MiniMax H3 Community License](https://huggingface.co/Lakonik/pi-H3/blob/main/LICENSE.md).

| Role | File | Size | Profile | Notes |
|---|---|---:|---|---|
| Transformer (FL2VA, pruned) | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 21.0 GB | minimal | The base upstream pi-H3 workflows use. FL2VA = first/last-frame to video+audio |
| Text encoder | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15.7 GB | minimal | Qwen3-VL 32B in NVFP4 (native FP4 on Blackwell) |
| Video VAE | `minimax_h3_video_vae_int8_convrot.safetensors` | 2.8 GB | minimal | In DWD mode it only **encodes** the keyframes. `_fp16` (5.2 GB) is accepted instead if present |
| Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` | 0.6 GB | minimal | Decodes the audio latents |
| pi-H3 2-step DWD adapter | `pi_h3_2step_dwd_adapter_int8_convrot.safetensors` | 2.2 GB | minimal | pi-Flow v2 LoRA + DWD pixel refiner |
| pi-H3 4-step DWD adapter | `pi_h3_4step_dwd_adapter_int8_convrot.safetensors` | 2.2 GB | full | Better on complex motion; about 2x denoise time |

Sizes are the HF LFS sizes; `download_models.sh` checks each file against them.

## Alternatives (not wired in by default)

| File | Size | Why you might want it | Caveat |
|---|---:|---|---|
| `minimax_h3_fl2va_pruned_w6a8.safetensors` | 16.0 GB | 5 GB less disk; might help 16 GB cards | **Untested** with pi-H3 adapters, which were converted against the int8 ConvRot base. Try `--unet minimax_h3_fl2va_pruned_w6a8.safetensors` and compare at a fixed seed |
| `minimax_h3_fl2va_pruned_fp8_scaled.safetensors` | 21.0 GB | FP8 path | Same size as int8; no reason to switch |
| `qwen3vl_32b_minimax_h3_int8_convrot.safetensors` | 27.1 GB | GPUs without FP4 (Ada / RTX 4080, Ampere) might run INT8 faster than emulated NVFP4 | 11 GB larger; untested here |
| `pi_h3_{2,4}step_adapter` (non-DWD) | 0.5 GB each | VAE-decoded output instead of DWD | Needs the VAE decode path, which h3gen doesn't build yet |

Fetch any of these with
`EXTRA_MODELS="minimal diffusion_models/<file> Comfy-Org/MiniMax-H3 diffusion_models/<file>" bash scripts/download_models.sh`,
then pass `--unet/--clip/...` to h3gen.

## Disk math

`minimal` comes to about 42.3 GB of models and `full` to about 44.5 GB, plus about 7 GB of runtime. The full
table and the ways to cut disk are in the [README](../README.md#disk-requirements).
