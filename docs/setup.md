# Setup

## Prerequisites

- Windows 11 + WSL2 with an NVIDIA driver that exposes CUDA 13 to WSL. `nvidia-smi` inside the distro must show
  the GPU. Tested with driver 610.88 (CUDA 13.3 UMD).
- A WSL distro (tested: Ubuntu 24.04) with `git`, `curl`, `python3` (3.10+ for h3gen) and
  [uv](https://docs.astral.sh/uv/). uv installs its own managed Python 3.12 for the ComfyUI venv.
- No system CUDA toolkit is needed; the torch cu130 wheels bring their own. If `LD_LIBRARY_PATH` points at a
  different CUDA, `serve.sh` unsets it.
- Disk: about 49 GB on the Linux filesystem for a fresh `minimal` install (see the README's Disk requirements).
- RAM: 54 GB worked. Peak use during a 1344x768 run was about 45 GB, because ComfyUI keeps offloaded weights in
  RAM. Below about 48 GB, expect swapping; see hardware.md.

## Steps

```bash
# inside WSL, in the repo (e.g. /mnt/c/<path>/h3-video-gen)
bash scripts/setup.sh               # 1. ComfyUI + venv + ComfyUI-piFlow; writes ~/h3-video-gen-runtime/versions.txt
bash scripts/download_models.sh     # 2. models (minimal profile); re-run any time, it resumes and size-checks
bash scripts/fetch_samples.sh       # 3. sample images
bash scripts/serve.sh               # 4. start ComfyUI on 127.0.0.1:8190 (background, waits for the API)
scripts/h3gen check                 # 5. JSON readiness report; "ready": true
scripts/h3gen example distracted-boyfriend   # 6. smoke test (about 40 s on a 5090 including the cold load)
```

From PowerShell, use `.\scripts\wsl.ps1 <setup|download_models|fetch_samples|serve|stop|status>` and
`.\scripts\wsl.ps1 h3gen ...`.

## Configuration

Copy `config/h3gen.env.example` to `config/h3gen.env` (gitignored). Variables you can set:

| Var | Default | Meaning |
|---|---|---|
| `H3_RUNTIME` | `~/h3-video-gen-runtime` | ComfyUI, venv, models, logs, raw outputs |
| `H3_PORT` | `8190` | ComfyUI port |
| `H3_SHARED_MODELS` | empty (off) | An existing ComfyUI `models/` folder to reuse read-only |
| `H3_WSL_DISTRO` | WSL default distro | Distro that `scripts/wsl.ps1` runs in (`$env:H3_WSL_DISTRO` wins) |
| `H3_PROFILE` | `minimal` | `minimal` or `full` (adds the 4-step adapter) |
| `COMFY_REF` / `PIFLOW_REF` | `v0.46.2` / `4355cc4794` | Pinned upstream versions (piFlow v1.4.2 + #44) |
| `H3_SPARK` | `0` | `1` makes every `setup` install Spark-Attn, like `setup.sh --spark` |
| `SPARK_VERSION` | `0.2.0` | Spark-H3 release; its per-arch sha256 pins are in `scripts/_env.sh` |
| `TORCH_INDEX` | cu130 wheel index | Blackwell (sm_120) needs cu128 or newer |

## Optional: Spark-Attn

[Spark-H3](https://github.com/zechengtang/Spark-H3) adds a sparse attention node that the pi-H3 authors
recommend over ComfyUI's built-in Sol, because it stays closest to dense attention. `bash scripts/setup.sh
--spark` (PowerShell: `.\scripts\wsl.ps1 setup --spark`) does the following:

1. Picks the Linux build for this GPU from `nvidia-smi` (sm86 = RTX 30, sm89 = RTX 40, sm120 = RTX 50 /
   RTX PRO Blackwell). There are no builds for other architectures.
2. Downloads the release zip (about 18 MB) to `~/h3-video-gen-runtime/downloads/` and checks it against the
   sha256 pinned in `scripts/_env.sh`.
3. Extracts it to `ComfyUI/custom_nodes/ComfyUI-Spark-H3`. For sm86/sm89 it unhides the node, which v0.2.0's
   Linux archives hide by mistake.
4. Runs its `install.py` with the venv's Python. That installs the bundled `spark-h3-kitchen` kernel wheel
   (0.2.37, the release's recommended build) next to ComfyUI's official `comfy-kitchen`, which is left
   unchanged.

Restart the server afterwards (`stop`, then `serve`). `h3gen check` lists the node under `spark_attention`.

Things to know:

- **Prebuilt binary.** The author compiled the kernel library and uploaded it by hand; GitHub's CI didn't build
  it. On 2026-11-23 the release's Python files and the wheels' Python and header files were checked against the
  public sources and matched byte for byte, but the compiled `_C.abi3.so` can't be verified that way. See
  [work-notes/2026-11-25-spark-attn.md](../work-notes/2026-11-25-spark-attn.md).
- **Versions.** Spark-H3 0.2.0 lists ComfyUI 0.38–0.44 as supported and was release-tested on torch 2.12. It
  works here on ComfyUI 0.46.2 with torch 2.14.1.
- **Remove it:** `rm -rf ~/h3-video-gen-runtime/ComfyUI/custom_nodes/ComfyUI-Spark-H3`, then
  `uv pip uninstall --python ~/h3-video-gen-runtime/ComfyUI/.venv/bin/python spark-h3-kitchen`.

## Another machine (e.g. RTX 4080 box)

Clone the repo and run the same steps. If the machine already has a ComfyUI model folder with these files, set
`H3_SHARED_MODELS` to it; otherwise every file is downloaded. Read [hardware.md](hardware.md) first for 16 GB cards.

## Uninstall

`bash scripts/stop.sh && rm -rf ~/h3-video-gen-runtime`. This removes everything except the repo and the shared
folder, which is never touched.
