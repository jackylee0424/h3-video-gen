# AGENTS.md: operating manual for AI agents

This repo generates video+audio from reference images with pi-H3 on a local NVIDIA GPU. Read this first. Use
[README.md](README.md) for the human overview and [docs/](docs/) for details.

## Ground truth about the environment

- **Machine-specific facts** (which distro, other projects on the box, folders you must not touch) are in
  `AGENTS.local.md` at the repo root when it exists. It's gitignored. Read it first, and put such facts there,
  never in tracked files.
- Host: Windows 11 with the repo on a Windows drive (`C:\...` is `/mnt/c/...` inside WSL).
- Compute runs **inside a WSL2 distro** (Ubuntu 24.04 tested) with GPU passthrough. `scripts/wsl.ps1` uses
  `$env:H3_WSL_DISTRO`, else `H3_WSL_DISTRO` in `config/h3gen.env`, else the WSL default distro.
- Runtime (ComfyUI, venv, downloaded models, logs, raw ComfyUI output) lives in `~/h3-video-gen-runtime` inside
  WSL, **not** in this repo. Don't put venvs or models under `/mnt/c`.
- `H3_SHARED_MODELS` (set in `config/h3gen.env`) may point at another ComfyUI install's `models/` folder. Treat it
  as read-only: never modify that install, start it or stop it.
- Our ComfyUI listens on `127.0.0.1:8190`. Run only one heavy GPU job at a time.

## Commands (from PowerShell; inside WSL use `bash scripts/X.sh` / `scripts/h3gen`)

| Goal | Command | Notes |
|---|---|---|
| Health check | `.\scripts\wsl.ps1 status` | exit 0 + `READY` when generation can run |
| Install / repair runtime | `.\scripts\wsl.ps1 setup` | idempotent; pinned versions in `scripts/_env.sh` |
| Models | `.\scripts\wsl.ps1 download_models [--profile full] [--dry-run]` | resumable; size-checked |
| Sample images | `.\scripts\wsl.ps1 fetch_samples` | sha256-checked |
| Start / stop server | `.\scripts\wsl.ps1 serve` / `stop` | serve waits until the API answers |
| Readiness as JSON | `.\scripts\wsl.ps1 h3gen check` | lists the resolved model files |
| Run a preset | `.\scripts\wsl.ps1 h3gen example <id> [--steps 4] [--seed N]` | ids: `h3gen example --list` |
| Generate | `.\scripts\wsl.ps1 h3gen generate --first IMG [--last IMG] --prompt-file P.txt` | see docs/usage.md |
| Inspect graph | add `--dry-run` | prints the settings and the API graph, queues nothing |

`h3gen` prints progress on stderr and **one JSON object per video on stdout**: `output`, `wall_seconds`,
`execution_seconds` and `settings`. The same JSON is saved next to the mp4 as `outputs/<name>.json`.

## Rules

1. **Long jobs:** model loading on the first run takes minutes; a 5 s clip takes tens of seconds once warm. Run
   generations in the background and wait for completion instead of polling in a tight loop.
2. **Prompts follow the MiniMax H3 format.** It has a reference-alignment line,
   `integrated_multimodal_description`, `overall_soundscape` and `non_diegetic_music`. Copy the skeletons in
   [docs/prompting.md](docs/prompting.md); free-form prompts give worse results.
3. **Seeds:** always pass `--seed` when results need to be compared or reproduced. The seed is in the sidecar.
4. **Keep the record in work-notes.** After any experiment (new settings, a failure, timings, a version bump),
   add or extend a dated file in [work-notes/](work-notes/) in the format given in work-notes/README.md. Durable
   conclusions go into docs/; background reading and comparisons go into research/.
5. **Version bumps** (ComfyUI, ComfyUI-piFlow, torch) go through `scripts/_env.sh` pins, then `setup`, then a test
   render, then a work-note. Keep the bump only if `h3gen example distracted-boyfriend` still works.
6. Don't commit `outputs/`, `samples/images/`, model files or `config/h3gen.env`. They are already gitignored.
7. Disk and download budget: the default profile is `minimal`; see the "Disk requirements" section of the README.
   Ask before downloading more than about 5 GB that isn't on the default list.

## Where things are

- Graph definition (which nodes, which settings): [h3gen/graph.py](h3gen/graph.py). It mirrors upstream
  `ComfyUI-piFlow/workflows/pi-H3-DWD.json`. If upstream changes, update it here and record the change in a
  work-note.
- ComfyUI HTTP client: [h3gen/comfy.py](h3gen/comfy.py). CLI: [h3gen/cli.py](h3gen/cli.py).
- Server log: `~/h3-video-gen-runtime/comfyui.log` (WSL). Installed versions: `~/h3-video-gen-runtime/versions.txt`.
- Failure playbook: [docs/troubleshooting.md](docs/troubleshooting.md).
