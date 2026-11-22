# pi-H3: what it is

Read 2026-11-21. Sources: the [pi-H3 blog](https://hanshengchen.com/blog/pi-h3/), the
[model card](https://huggingface.co/Lakonik/pi-H3),
[LakonLab docs/piH3.md](https://github.com/Lakonik/LakonLab/blob/main/docs/piH3.md),
[ComfyUI-piFlow docs/piH3.md](https://github.com/Lakonik/ComfyUI-piFlow/blob/main/docs/piH3.md), and the
[Space app.py](https://huggingface.co/spaces/Lakonik/pi-H3/blob/main/app.py).

## Summary

- **Base model:** MiniMax H3 generates **video and synchronized audio together** from text, optionally
  conditioned on a first and/or last frame (the FL2VA variant). It runs at 24 fps with `17n+5` frames. The
  text encoder is Qwen3-VL 32B. The distributed "pruned" transformer is about 20B parameters (40 GB in bf16).
- **pi-Flow v2:** data-free, few-step distillation into 2- or 4-step LoRA-style adapters. The blog says v2's
  straighter trajectories remove the need for pi-Flow v1's substep integration. Details are deferred to a paper.
- **DWD (Decoding Without a Decoder)** ([paper](https://arxiv.org/abs/2611.22287),
  [project](https://hanshengchen.com/dwd/)): at the last step the denoiser predicts **pixels** directly, so the
  large H3 video VAE decoder (5–10 GB) never runs. In v1.0 the pixel refiner is a windowed-attention transformer
  that reuses 8 of the 24 blocks of the Sol-H3-VAE decoder. It replaced v0.9's convolutional refiner, which was
  blurrier and used more VRAM. The authors call DWD on H3 "still experimental" because of H3's high compression
  (one token covers 4x32x32x3 pixel values).
- **Sol-Attn:** forward-only sparse attention vendored from NVIDIA's Sol engine. Kernels exist for SM90,
  SM100/103 and SM120; on SM120 it uses block-sparse attention. The first 2 blocks stay dense.
- **Releases:** v0.9 on 2026-11-10 (demo only; the blog numbers come from it) and v1.0 on 2026-11-21 (weights,
  LakonLab code, ComfyUI nodes). Training code is still to come.

## Upstream speed claims (not measured here)

| Setup | 5 s | 10 s | 15 s |
|---|---:|---:|---:|
| B200, 1344x768, FP8 W8A8, Sol on cuDNN BSA, 2-step | 3.8 s | 9.2 s | 18.6 s |
| B200, same, 4-step | 7.3 s | 17.6 s | 36.4 s |
| Sol-H3 4-step baseline (B200) | 9.5 s | 24.3 s | 45.0 s |
| RTX 3090 unlocked, CUDA 13, ComfyUI INT8 ConvRot, Sol, 2-step, 1344x768, prompt pre-encoded | 38.5 s | 97.6 s | 186.1 s |
| RTX 3090, same, 864x480 | 15.5 s | 37.3 s | 69.2 s |

Quality claims are qualitative only (no FVD/VBench): the 4-step result is said to beat other 4–8-step H3
accelerations, and the 2-step result is said to be "already sufficient for simpler scenes".

**Measured here (RTX 5090):** see [docs/hardware.md](../docs/hardware.md). 5 s at 1344x768 ran in about 25 s
warm, end to end including text encoding; 10 s took about 47 s.

## Settings in the official code

From the Space `app.py` and the ComfyUI workflow:
- schedulers: `FlowEulerODEScheduler(shift=12 video / 3 audio, max_raw_t=0.93 (2-step) | 0.96 (4-step),
  final_step_size_scale=0.6)`
- canvas: aspect ratio at N megapixels, rounded up to a multiple of 32
- keyframes: `ImageOps.fit` (center crop, Lanczos)
- frames: `clamp(round((s*24-5)/17), 7, 20)*17+5`
- output: yuv420p H.264, CRF 23

## Open questions / ideas

- DWD versus VAE-decoded (non-DWD adapters) quality at a fixed seed. That needs a VAE-decode variant of the graph.
- Whether the w6a8 transformer works with the int8-converted adapters (it would save 5 GB of disk and VRAM).
- 4-step versus 2-step on keyframe-heavy prompts.
