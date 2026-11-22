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
| `COMFY_REF` / `PIFLOW_REF` | `v0.46.2` / `bcb6ffb8ff` | Pinned upstream versions |
| `TORCH_INDEX` | cu130 wheel index | Blackwell (sm_120) needs cu128 or newer |

## Another machine (e.g. RTX 4080 box)

Clone the repo and run the same steps. If the machine already has a ComfyUI model folder with these files, set
`H3_SHARED_MODELS` to it; otherwise every file is downloaded. Read [hardware.md](hardware.md) first for 16 GB cards.

## Uninstall

`bash scripts/stop.sh && rm -rf ~/h3-video-gen-runtime`. This removes everything except the repo and the shared
folder, which is never touched.
