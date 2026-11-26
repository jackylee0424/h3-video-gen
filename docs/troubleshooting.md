# Troubleshooting

Start with `.\scripts\wsl.ps1 status` and `.\scripts\wsl.ps1 h3gen check`, then read the server log:
`wsl -d <distro> -- tail -100 ~/h3-video-gen-runtime/comfyui.log`.

| Symptom | Cause | Fix |
|---|---|---|
| `cannot reach ComfyUI at http://127.0.0.1:8190` | Server not running | `bash scripts/serve.sh`; if it exits right away, the log tail is printed |
| `serve.sh` says "already running" but h3gen can't connect from Windows | WSL localhost forwarding off | Run h3gen inside WSL (`scripts/h3gen`), or enable `localhostForwarding` in `.wslconfig` |
| `node 'Load LakonLab Adapter' not registered` / `missing_nodes` not empty | ComfyUI-piFlow missing or failed to import | `bash scripts/setup.sh`; grep the log for `ComfyUI-piFlow` / `IMPORT FAILED`. piFlow 1.4 needs ComfyUI ≥ 0.45 |
| `... not found (bash scripts/download_models.sh ...)` | Model file missing | Run the suggested command. 4-step needs `--profile full` |
| `SIZE MISMATCH` from download_models | Truncated or old file | Delete the named file and re-run (downloads resume through `.part`) |
| `graph rejected: {...}` | Node inputs changed upstream (version bump) | Compare `curl localhost:8190/object_info/<Node>` with `h3gen/graph.py`; fix, then write a work-note |
| `execution failed: ... OutOfMemory` | VRAM or RAM exhausted | Lower `--megapixels` / `--seconds`; stop other GPU users; `serve.sh -- --lowvram`; check `free -g` in WSL |
| WSL becomes unresponsive or the process is killed during load | System RAM exhausted (about 45 GB peak) | Close other WSL workloads; raise WSL `memory=` / swap in `.wslconfig` |
| `CUBLAS_STATUS_INVALID_VALUE` | A system CUDA on `LD_LIBRARY_PATH` | `serve.sh` already unsets it; don't launch ComfyUI any other way |
| Error mentioning Sol / block-sparse kernels | GPU arch without Sol kernels, or a kernel compile problem | Re-run with `--dense` to confirm, then note it |
| `Spark-Attn node not registered` | Spark-H3 not installed, or the server was started before installing it | `bash scripts/setup.sh --spark`, then `stop` and `serve`; grep the log for `ComfyUI-Spark-H3` |
| `setup.sh --spark`: `no Linux build for smXX` | Spark-H3 ships only sm86, sm89 and sm120 builds | Use `--attention sol` |
| `[Spark-H3] ... backend` error from `install.py`, or the node fails to import | The prebuilt kernel wheel doesn't load with this torch/CUDA (built for CUDA 13.0) | Check `versions.txt` against the release notes; uninstall it (docs/setup.md) and use `--attention sol` |
| Visible grid or block seams in Sol videos | `extra_tokens` 256 (h3gen before piFlow 1.4.1) | Fixed: graph.py now sends 0, as upstream does |
| Garbled non-ASCII text in prompts (`Â¿`) | File read as cp1252 on Windows | Save prompt files as UTF-8; h3gen reads `--prompt-file` as UTF-8 |
| Output looks unlike the reference image | Prompt doesn't restate the image / no alignment line | See prompting.md: the alignment line plus "preserving their exact positions…" |
| GPU busy / out of memory | Another ComfyUI or GPU job is running | Don't stop it yourself; ask the user. Ours uses port 8190 |
| Warm runs with a new prompt take about 2x longer than in hardware.md; same-prompt reruns stay fast | Windows host is short of RAM and pages out the WSL VM (Task Manager: `vmmemWSL` working set well below WSL's `free -g` "used"), so reloading the 15 GB text encoder hits disk | Free host RAM (close apps), or lower WSL `memory=` in `.wslconfig` so the VM isn't paged. Check sampling speed alone by rerunning the same prompt with another `--seed` |
