# 2026-11-21: Move to the h3-video-gen repo, rename the runtime, re-test

**Goal:** continue in the new `h3-video-gen` repo (clean history), rename everything to the new name, and check
that generation still works end to end.

## Setup

Same versions as [the bootstrap note](2026-11-21-bootstrap.md): `setup` was re-run and changed no packages, and
`versions.txt` is identical. Models are unchanged. Machine-specific values (WSL distro, shared model folder) now
live only in the gitignored `config/h3gen.env`.

## What was done

- Repo, docs and default runtime folder renamed: `h3-vid-gen` → `h3-video-gen`, and `~/h3-vid-gen-runtime` →
  `~/h3-video-gen-runtime` (`H3_RUNTIME` default in `scripts/_env.sh`). The existing runtime was moved with `mv`,
  then the old path was rewritten in `ComfyUI/extra_model_paths.yaml` and the venv's `bin/` scripts (activate,
  console-script shebangs). The venv's `python` links to uv's absolute interpreter path, so it survives the move.
  Then `bash scripts/setup.sh` was re-run (idempotent).
- Two `scripts/wsl.ps1` bugs found and fixed:
  1. With no extra arguments, `$Rest | ForEach-Object` still ran once and passed an empty `''` argument.
     `serve` forwarded it to ComfyUI, giving `main.py: error: unrecognized arguments:`. `serve` had only been
     run inside WSL before, so this hadn't shown up.
  2. `$ErrorActionPreference = 'Stop'` made Windows PowerShell 5.1 turn the first stderr line into a
     terminating error whenever output was redirected (`2>&1`, `*> file`). That killed `setup` mid-install.
     The wrapper now relaxes it for the `wsl` call.

```powershell
.\scripts\wsl.ps1 serve
.\scripts\wsl.ps1 h3gen example distracted-boyfriend --seed 1262275999          # cold
.\scripts\wsl.ps1 h3gen example render-outlived-you --seed 1034413408           # warm, new prompt
.\scripts\wsl.ps1 h3gen example render-outlived-you --seed 7                    # warm, cached prompt encoding
```

## Results (2-step DWD, Sol, 1344x768, 124 frames)

| Run | Wall | Exec | Sampling | Output |
|---|---:|---:|---|---|
| distracted-boyfriend, cold | 55.2 s | 52.5 s | init 15 s | `20261121-201932_distracted-boyfriend_s1262275999_2step.mp4` |
| render-outlived-you, warm (new prompt) | 48.2 s | 46.8 s | init 37 s | `20261121-202039_render-outlived-you_s1034413408_2step.mp4` |
| render-outlived-you, seed 7 (prompt cached) | 14.0 s | 13.0 s | 5.3–5.7 s/it | `20261121-202213_render-outlived-you_s7_2step.mp4` |

- **Output check:** the distracted-boyfriend contact sheet matches the morning run. Frame 0 matches the
  reference, the action follows the prompt, and the audio is AAC stereo 32 kHz with RMS 0.095 (0.097 in the
  morning).
- **Slower than the morning (38.8 s cold, 24.8 s warm):** sampling itself is faster (5.5 against 7.2 s/it),
  so the extra time is in reloading weights, mostly the 15 GB text encoder. The Windows host had 7.3 of 63.4 GB
  free, and `vmmemWSL` had a 30.5 GB working set while WSL reported 46 GB used. So the host was paging the VM's
  memory to disk. ComfyUI RSS was about 50 GB.

## Conclusions / follow-ups

- Rename and runtime move work. → README, AGENTS.md, docs updated.
- `wsl.ps1` fixes. → code. Use `wsl.ps1 serve` from PowerShell now that it works.
- Host RAM pressure explains slow warm runs with new prompts. → docs/troubleshooting.md. The hardware.md
  numbers (morning) stay the reference for an unloaded host.
