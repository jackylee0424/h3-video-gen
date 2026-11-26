# Hardware

## Measured: RTX 5090 (32 GB, sm_120) in WSL2, 54 GB RAM

This table: ComfyUI v0.46.2, ComfyUI-piFlow v1.4.0, torch 2.14.1+cu130, int8 ConvRot transformer, nvfp4 text encoder,
Sol sparse attention, 2-step DWD adapter, 1344x768. Wall time is from h3gen submit to the mp4 on disk.

| Run | Frames | Wall | Notes |
|---|---:|---:|---|
| distracted-boyfriend (first frame), **cold** | 124 (5.17 s) | 38.8 s | Includes loading every model from disk; sampling about 14.5 s |
| render-outlived-you (text only), warm | 124 (5.17 s) | 24.8 s | |
| woman-yelling-at-cat (first+last), warm | 243 (10.12 s) | 47.3 s | |

Resource use during these runs: about 27 GB of VRAM allocated (ComfyUI dynamic VRAM; weights stream from RAM),
and **about 45 of 54 GB of system RAM used**. RAM is the binding limit in WSL. Don't run other large jobs, such
as another ComfyUI instance, at the same time.

### Sparse attention on the 5090 (2026-11-25, piFlow v1.4.2, Spark-H3 0.2.0)

distracted-boyfriend, 1344x768, 124 frames, 2 steps, host not short of RAM. Same seed for the quality columns;
the speed columns are from seed 7 with the prompt already encoded.

| `--attention` | Sampling per step | Exec, prompt encoded | Sharpness vs dense | PSNR vs dense |
|---|---:|---:|---:|---:|
| `dense` | 15.1 s | (31.2 s, model switch included) | 100% | – |
| `sol` (built-in, `extra_tokens` 0) | 6.45 s | 14.8 s | 67% | 14.7 dB |
| `spark` (speed mode) | 6.76 s | 14.9 s | 98% | 18.1 dB |

Both sparse methods are about 2.3x faster per step than dense. End to end, Spark costs about 0.1 s more than
Sol here, but it keeps dense's sharpness and stays closer to dense's motion, which matches the pi-H3 authors'
advice. Sharpness is the variance of the Laplacian; PSNR is the per-frame mean over the clip and falls as the
motion diverges. See [work-notes/2026-11-25-spark-attn.md](../work-notes/2026-11-25-spark-attn.md).

For comparison, the authors report about 38.5 s for a 5 s 1344x768 clip on an unlocked RTX 3090 (24 GB), with
the prompt already encoded, and 3.8 s on a B200 (FP8, cuDNN block-sparse attention). See
[research/pi-h3.md](../research/pi-h3.md).

## RTX 4080 (16 GB, sm_89): guidance, untested here

- **VRAM:** the transformer alone is 21 GB in int8, so ComfyUI will offload part of it to RAM every step. Expect
  it to work but run slower. Start with `--megapixels 0.5` and 5 s, and keep `serve.sh` default flags first; if
  it OOMs, try `bash scripts/serve.sh -- --lowvram`.
- **RAM:** offloading moves the pressure to system RAM. Plan for 64 GB of RAM (WSL needs about 48 GB or more
  visible; raise it with `memory=` in `%UserProfile%\.wslconfig`).
- **Text encoder:** NVFP4 has no native tensor-core support on Ada. If text encoding is slow, try the
  `qwen3vl_32b_minimax_h3_int8_convrot` text encoder (27 GB; see models.md).
- **Smaller transformer:** `minimax_h3_fl2va_pruned_w6a8` (16 GB) is the obvious thing to try, but it is
  untested with the pi-H3 adapters. Compare at a fixed seed before trusting it.
- **Sparse attention:** Spark-H3 ships an SM89 build (`setup.sh --spark` picks it), and the pi-H3 authors publish
  an SM89 Spark workflow, so try `--attention spark` first. Built-in Sol has kernels for SM90/SM100/SM120; on
  SM89, ComfyUI's `BlockSparseAttention` may fall back to something else or fail. If either errors, use
  `--dense`.
- Record what you find in a work-note and update this section.

## Throughput knobs (fastest first)

1. Lower `--megapixels` (token count falls with the pixel count; attention cost falls even faster).
2. Shorter `--seconds` (frames).
3. 2 steps instead of 4.
4. Keep sparse attention on (`--attention auto`, the default: Spark if installed, else Sol); `--dense` is a
   debugging switch.
5. Keep the server running. A cold start costs about 15 s more on the 5090, mostly model loading.
