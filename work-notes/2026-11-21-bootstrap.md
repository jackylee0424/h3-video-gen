# 2026-11-21: Bootstrap: repo, WSL runtime, first renders on the RTX 5090

**Goal:** reproduce the [pi-H3 Space](https://huggingface.co/spaces/Lakonik/pi-H3) locally (image-to-video with
audio) on the RTX 5090, headless and scriptable, inside WSL2.

## Findings before building

- The Space runs LakonLab/diffusers from a 133 GB bf16 repo with FP8 quantization at load time. That's too big
  for 54 GB of WSL RAM, so it was rejected (research/deployment-options.md).
- The authors ship a ComfyUI path (ComfyUI-piFlow v1.4.0, released today) with INT8 ConvRot adapters, which they
  test on a 24 GB RTX 3090. Chosen.
- WSL already had another project's ComfyUI install (v0.42.1) with the H3 int8 transformer,
  nvfp4 text encoder, and fp16 video and audio VAEs, all matching HF sizes. piFlow needs ComfyUI ≥ 0.45, so we
  install our own ComfyUI and reuse those models read-only (`H3_SHARED_MODELS`).
- The upstream workflow `pi-H3-DWD.json` uses subgraphs ("pi-H3 Adapter", "Frame Count") and dynamic combos, so
  it was rebuilt as an API graph in `h3gen/graph.py` from `/object_info`. Dynamic combo keys are flattened as
  `selection.tau` and `format.codec`; ComfyUI accepted them.

## Setup

```
python 3.12.13 | torch 2.14.1+cu130 (cuda 13.0) | GPU RTX 5090 sm_120 | driver 610.88
comfyui v0.46.2 | comfyui-piflow bcb6ffb (v1.4.0) | comfyui-frontend 1.59.6 | av 19.0.2 | triton 3.8.0
models: minimax_h3_fl2va_pruned_int8_convrot (shared), qwen3vl_32b_minimax_h3_nvfp4_awq (shared),
        minimax_h3_video_vae_int8_convrot (downloaded), minimax_h3_audio_vae_fp32 (shared),
        pi_h3_2step_dwd_adapter_int8_convrot (downloaded)
```

New downloads were about 5 GB: the int8 VAE (2.8 GB) and the 2-step adapter (2.2 GB). The 4-step adapter
download was cancelled when the default became the `minimal` profile, at the user's request to cut disk.

## What was done

```bash
bash scripts/setup.sh && bash scripts/download_models.sh && bash scripts/fetch_samples.sh && bash scripts/serve.sh
scripts/h3gen check
scripts/h3gen example distracted-boyfriend                      # cold
scripts/h3gen example render-outlived-you woman-yelling-at-cat  # warm
```

## Results (2-step DWD, Sol attention, 1344x768, original Space seeds)

| Example | Mode | Frames | Wall | Exec | Audio | Output |
|---|---|---:|---:|---:|---|---|
| distracted-boyfriend | first frame | 124 | 38.8 s (cold) | 37.7 s | AAC stereo 32 kHz, RMS 0.097 | `20261121-104301_distracted-boyfriend_s1262275999_2step.mp4` |
| render-outlived-you | text only | 124 | 24.8 s | 25.2 s* | RMS 0.181 | `20261121-104415_render-outlived-you_s1034413408_2step.mp4` |
| woman-yelling-at-cat | first + last | 243 | 47.3 s | 48.7 s* | RMS 0.034 | `20261121-104440_woman-yelling-at-cat_s14851915_2step.mp4` |

\* from the ComfyUI log ("Prompt executed in …"). The cold run's sampling was about 14.5 s for 2 steps (7.2 s/it)
after model init.

Visual check (contact sheets):
- **distracted-boyfriend:** frame 0 matches the reference. The man lets go of his girlfriend's hand, both
  gesture, and the woman in red walks out on the left. Coherent identities and no obvious artifacts.
- **render-outlived-you:** a slow push-in with the "99%" screen text legible throughout. On-prompt.
- **woman-yelling-at-cat:** shot 1 animates the first frame (pointing, shouting). It cuts to the cat at about
  5.7 s, a hand pets the cat, and it ends on the composition of the last-frame reference. Matches the prompt.

The user generated the same distracted-boyfriend preset on the hosted Space for comparison (same seed and
settings). Upstream uses FP8 and LakonLab kernels, so the frames are not expected to be bit-identical.

Resources: about 27 GB of VRAM allocated after a run, and **system RAM peaked at about 45 / 54 GB**.

## Conclusions / follow-ups

- Local pi-H3 works end to end on the 5090 and roughly 1.5x faster than the authors' RTX 3090 figure. → docs/hardware.md
- RAM is the tightest resource in WSL; don't run the other project's ComfyUI at the same time. → docs/hardware.md,
  troubleshooting.md
- To try next: the 4-step adapter (`--profile full`), and the w6a8 transformer at a fixed seed (disk/VRAM
  saving, 4080 relevance). Validate on an actual RTX 4080.
- Bug fixed along the way: on Windows, Python decoded the Space's examples.json as cp1252 (`¿` became `Â¿`), so
  `samples/examples.json` was regenerated from raw UTF-8 bytes.
