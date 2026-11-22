# Troubleshooting

Start with `.\scripts\wsl.ps1 status` and `.\scripts\wsl.ps1 h3gen check`, then read the server log:
`wsl -d <distro> -- tail -100 ~/h3-vid-gen-runtime/comfyui.log`.

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
| Garbled non-ASCII text in prompts (`Â¿`) | File read as cp1252 on Windows | Save prompt files as UTF-8; h3gen reads `--prompt-file` as UTF-8 |
| Output looks unlike the reference image | Prompt doesn't restate the image / no alignment line | See prompting.md: the alignment line plus "preserving their exact positions…" |
| GPU busy / out of memory | Another ComfyUI or GPU job is running | Don't stop it yourself; ask the user. Ours uses port 8190 |
