# Deployment options considered (2026-11-21)

Goal: run pi-H3 image-to-video locally on an RTX 5090 (32 GB) or RTX 4080 (16 GB), from WSL2 with 54 GB of RAM.

## Option A: the Space's own code (LakonLab + diffusers), rejected

- Loads `multimodalart/MiniMax-H3-Pruned` in **bf16**. The repo is 133 GB: transformer about 40 GB, plus an
  identical `transformer_ref` of about 40 GB, plus the Qwen3-VL text encoder at about 55 GB. It quantizes to FP8
  W8A8 at load time.
- Staging about 95 GB of bf16 weights before quantizing doesn't fit in 54 GB of RAM without custom
  layer-by-layer loading. The Space runs on a ZeroGPU "xlarge" slice and loads precompiled SM120 AOT artifacts
  tied to that environment.
- Pins `torch==2.11`, `transformers==5.16.1`, `diffusers==0.40.0` and `nvidia-cutlass-dsl` (for Sol).
- Its advantages, if a larger machine is ever available: FP8 W8A8, AOTInductor compilation, offline Sol bundles,
  and the official Gradio app (`demo/gradio_pih3.py --offload`).

## Option B: ComfyUI + ComfyUI-piFlow (INT8 ConvRot), chosen

- The authors publish this path for consumer GPUs and benchmark it on a 24 GB RTX 3090.
- Pre-quantized files: transformer int8 ConvRot (21 GB), text encoder NVFP4 (15.7 GB), video VAE int8 (2.8 GB),
  audio VAE (0.6 GB), adapters int8 (2.2 GB each). That's about 42–45 GB in total.
- ComfyUI's dynamic VRAM streams weights from RAM, so 32 GB of VRAM is comfortable and 16 GB is plausible.
- The test machine already had about 37 GB of these exact files in another ComfyUI install's models folder
  (sizes match HF). They're reused read-only through `H3_SHARED_MODELS`, which brought the new downloads down to about 7 GB.
- That install was ComfyUI v0.42.1 and belongs to another project, and piFlow 1.4 needs ≥ 0.45. So this repo installs its own ComfyUI v0.46.2 on port 8190.
- Headless control is through the HTTP API with an API-format graph built in Python (h3gen). The UI workflow
  JSON uses subgraphs and dynamic combos that don't convert to API format offline, so the graph is rebuilt by hand
  from `/object_info`.

## Option C: ComfyUI native H3 turbo LoRAs (not pi-H3), noted only

The shared folder also has `minimax_h3_fl2v_turbo_8step` and `fasth3_vsa_gate`. These are other H3
accelerations. They're out of scope here but could serve as a quality and speed baseline later.

## Memory math (int8 path)

| Component | Weights |
|---|---:|
| Transformer + pi-H3 adapter | 21 + 2.2 GB |
| Text encoder (only during encoding) | 15.7 GB |
| Video VAE (encode keyframes only) / audio VAE | 2.8 / 0.6 GB |
| Activations at 1344x768x124 frames | several GB; grows with frames x pixels |

That's about 42 GB of weights against 32 GB of VRAM, so ComfyUI keeps part of it in RAM and swaps the text
encoder and transformer between them. The measured peak was about 45 GB of RAM in use. On 16 GB of VRAM,
offload goes up a lot: expect slower steps and plan for at least 64 GB of RAM.
