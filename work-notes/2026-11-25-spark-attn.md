# 2026-11-25: piFlow 1.4.2, Sol seam fix, Spark-Attn A/B

**Goal:** check whether a reported pi-H3 speedup (a 13.3 s 2-step render on a 5090 using Spark-Attn) applies
here. Then adopt piFlow 1.4.1's Sol seam fix, and try Spark-Attn against built-in Sol and dense attention.

## Background

- The reported 13.3 s is the same pi-H3 2-step DWD setup we already run: 13.0 s on 2026-11-21 with the prompt
  encoded. Its "9.9x" compares pi-H3 with stock H3, so there was no new speedup.
- Two upstream changes since our pin (piFlow v1.4.0, `bcb6ffb8ff`) were worth taking:
  - **v1.4.1:** Sol `extra_tokens` 256 → 0, because 256 "leaves block seams" and costs the same time.
  - **v1.4.2:** recommends Spark-Attn ([Spark-H3](https://github.com/zechengtang/Spark-H3)) as "closest to
    dense".
  - Main also has #40 and #44, two fixes for how the DWD head frees memory and loads its weights.

## Spark-H3 0.2.0 safety review (2026-11-23, before installing)

The release has only prebuilt binaries. The author compiled them and uploaded them by hand; the repo's CI only
packages the registry zip, which has no wheels. Checked statically on the SM120 Linux zip, without running it:

| Check | Result |
|---|---|
| sha256 against SHA256SUMS.txt and GitHub's asset digest | match (`b51a3ab2…858d`) |
| Archive paths, symlinks | none unsafe |
| 50 node files against the repo at tag `comfyui-v0.2.0` (`1fc6d44`) | 40 identical, all code included. The other 10: the version field in 5 workflow JSONs, generated packaging (`__init__.py`, which also hides the other archs' nodes; a one-line `h3_sparse_attention/__init__.py`; `pyproject.toml`; `spark_h3_build.json`), and a README that has no counterpart in the repo |
| Both wheels (0.2.37, 0.2.39): `.py`/`.h`/`.cuh` against official `Comfy-Org/comfy-kitchen` at the pinned revisions + the repo's patch + the documented rename | 53/53 and 55/55 byte-identical; RECORD hashes OK; no `.pth`, no entry points |
| Patch (about 2,460 added lines: sage_attention CUDA kernels) | no network, process or exec calls |
| `_C.abi3.so` dynamic imports | `socket/connect/bind/listen/dlopen/...`. The official comfy-kitchen 0.2.41 `.so` in our venv imports exactly the same set, and they come from the static CUDA runtime (`libcudart_static.a`). No `exec*`/`fork`/`system`/`getaddrinfo`/`send`/`recv`, no URLs or IPs, SM120 code only |
| `install.py` | runs `uv pip install --force-reinstall --no-deps` on the bundled wheel into the given Python. It leaves torch and the official comfy-kitchen alone. It only goes online when no bundled wheel matches |

The compiled code itself can't be verified this way; building from source would need CUDA Toolkit 13.0 (WSL has
13.2).

## Setup

- `scripts/_env.sh`:
  - `PIFLOW_REF` `bcb6ffb8ff` → `4355cc4794` (v1.4.2 + #44).
  - New Spark pins: `SPARK_VERSION` 0.2.0, plus sha256 for the sm86, sm89 and sm120 Linux zips.
- `scripts/setup.sh --spark` (or `H3_SPARK=1`):
  - Picks the arch from `nvidia-smi`, downloads the zip to `~/h3-video-gen-runtime/downloads/` and checks its sha256.
  - Extracts it to `custom_nodes/ComfyUI-Spark-H3`. For sm86/sm89 it also fixes the hidden-node bug that piFlow's
    docs describe.
  - Runs its `install.py` with the venv python.
- `h3gen/graph.py`:
  - Sol now sends `extra_tokens` 0.
  - New `attention` = `sol` / `spark` / `dense`. The Spark node values are copied from upstream
    `pi-H3-DWD-Spark-SM120.json` (speed mode, `topk_ratio` 0.2, no warmup, placed after the sigma shift). All 17
    inputs were checked against the server's `/object_info`.
- `h3gen/cli.py`:
  - `--attention auto|sol|spark|dense`. The default `auto` uses Spark when its node is registered, else Sol.
    `--dense` is kept as a shorthand.
  - `check` reports `spark_attention`.
  - Spark and dense outputs get an `_spark` / `_dense` filename suffix.

`versions.txt` after `setup --spark`. Only piFlow changed (before: `comfyui-piflow bcb6ffb`); the last three
lines are new:

```
python 3.12.13
torch 2.14.1+cu130 cuda 13.0 cuda_available True
gpu NVIDIA GeForce RTX 5090 sm_120
comfyui-frontend-package 1.59.6
av 19.0.2
numpy 2.5.4
safetensors 0.8.0
triton 3.8.0
comfy-kitchen 0.2.41
spark-h3-kitchen 0.2.37+spark.h3.sm120.cu130.1
comfyui v0.46.2
comfyui-piflow 4355cc4
comfyui-spark-h3 0.2.0 sm120
```

Spark-H3 lists ComfyUI ≤0.44 and was release-tested on torch 2.12 / Triton 3.7. Its installer's post-install
probe passed on torch 2.14.1 / Triton 3.8. At run time the log showed `[Spark-H3] active on SM120 (40090 packed
tokens, 37296 sparse-video tokens)` and `unexpected_fallbacks=[]`, with all 50 blocks sparse.

## What was done

```bash
bash scripts/setup.sh --spark          # from PowerShell: .\scripts\wsl.ps1 setup --spark
bash scripts/serve.sh
scripts/h3gen example distracted-boyfriend --attention sol   --seed 1262275999   # cold
scripts/h3gen example distracted-boyfriend --attention spark --seed 1262275999
scripts/h3gen example distracted-boyfriend --attention dense --seed 1262275999
scripts/h3gen example distracted-boyfriend --attention sol   --seed 7            # prompt encoded
scripts/h3gen example distracted-boyfriend --attention spark --seed 7
```

The quality comparison was a throwaway script (not in the repo). It decodes all 124 frames and computes three
measures against dense at the same seed: per-frame PSNR, the variance of the Laplacian (sharpness), and a
column-gradient ratio at 16/32/64-px boundaries (seams). It also builds a frame grid with a 2x crop.

The host had 45 of 63 GB free (no VM paging, unlike 2026-11-21), and the other ComfyUI on the machine was not
running.

## Results (2-step DWD, 1344x768, 124 frames)

| Run | Wall | Exec | Init + sampling | Output |
|---|---:|---:|---|---|
| sol, s1262275999, cold | 40.9 s | 39.8 s | 2 steps | `20261125-115737_distracted-boyfriend_s1262275999_2step.mp4` |
| spark, s1262275999 | 26.8 s | 26.1 s | init 17 s (first Spark run), 6.52 s/it | `20261125-115818_distracted-boyfriend_s1262275999_2step_spark.mp4` |
| dense, s1262275999 | 31.0 s | 29.7 s | 15.06 s/it | `20261125-115845_distracted-boyfriend_s1262275999_2step_dense.mp4` |
| sol, s7 | 14.6 s | 13.3 s | init 4 s, 6.45 s/it | `20261125-115916_distracted-boyfriend_s7_2step.mp4` |
| spark, s7 | 16.1 s | 14.9 s | init 5 s, 6.76 s/it | `20261125-115931_distracted-boyfriend_s7_2step_spark.mp4` |

The "exec" for seed 7 comes from the sidecar, and ComfyUI logged 14.81 s (sol) and 14.88 s (spark). So end to
end, Spark costs about 0.1 s more than Sol on the 5090. That matches the tweet's "about 0.2 s slower than Sol".
The extra 1.5 s of wall time for Spark at seed 7 is outside ComfyUI's execution (upload, queue, download); it
wasn't investigated.

Quality at seed 1262275999 against dense:

| | Sharpness (Laplacian var) | PSNR vs dense, mean / last frame | Seam ratio 16/32/64 px |
|---|---:|---|---|
| dense | 173.6 | – | 1.08 / 1.08 / 1.09 |
| sol (`extra_tokens` 0) | 116.1 (67%) | 14.7 / 13.3 dB | 1.12 / 1.14 / 1.17 |
| spark | 170.9 (98%) | 18.1 / 16.2 dB | 1.07 / 1.10 / 1.11 |

- **What the frame grid shows:** Spark follows dense closely. It has the same poses at frames 41, 82 and 123,
  and the same crisp plaid shirt in the 2x crop. Sol drifts by frame 82 (different body and arm poses, the
  woman's mouth wide open), its frame 123 differs, and it is visibly softer. All three keep frame 0 on the
  reference and follow the prompt.
- **Seams:** no visible seams in any of them. Sol still has a small excess at 64-px boundaries (1.17 against
  dense's 1.09), but it isn't visible. The seam fix wasn't A/B'd against `extra_tokens` 256; the change follows
  upstream.

## Conclusions / follow-ups

- **Spark-Attn is the better sparse attention here:** dense-level sharpness and motion at Sol's speed. It is now
  used automatically when installed (`--attention auto`). → docs/usage.md, docs/hardware.md, docs/setup.md
  (install, safety notes and removal), docs/architecture.md, troubleshooting.md, README, AGENTS.md.
- piFlow bump: `distracted-boyfriend` still renders (AGENTS.md rule 5). → `scripts/_env.sh`, docs/setup.md.
- Sparse attention (either kind) is about 2.3x faster per step than dense on the 5090.
- **Not done:**
  - Spark on an RTX 4080 (sm89): hardware.md now suggests trying it there first.
  - Longer clips: upstream reports Spark 8–10% faster than Sol at 10–15 s on a 3090.
  - Spark's `fidelity` mode.
- `wsl.ps1 ... *> file` still writes PowerShell `NativeCommandError` wrappers around stderr lines into the
  file. They're cosmetic: the run continues and the exit code is right.
