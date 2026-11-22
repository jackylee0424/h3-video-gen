#!/usr/bin/env bash
# Start the headless ComfyUI that h3gen talks to. Detaches by default and waits until the HTTP API answers.
#   bash scripts/serve.sh             # background; log in $H3_RUNTIME/comfyui.log
#   bash scripts/serve.sh --fg        # foreground (Ctrl+C stops it)
#   bash scripts/serve.sh -- --lowvram   # extra ComfyUI flags after --
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_env.sh"

FG=0; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --fg) FG=1 ;;
    --) shift; EXTRA=("$@"); break ;;
    *) EXTRA+=("$1") ;;
  esac
  shift
done

[ -x "$H3_VENV/bin/python" ] || { h3_log "runtime missing: run bash scripts/setup.sh"; exit 1; }
if curl -fs "http://$H3_HOST:$H3_PORT/system_stats" >/dev/null 2>&1; then
  h3_log "already running on http://$H3_HOST:$H3_PORT"; exit 0
fi

# Mismatched system CUDA libs on LD_LIBRARY_PATH break the torch wheel's cuBLAS (see docs/troubleshooting.md)
unset LD_LIBRARY_PATH
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
CMD=("$H3_VENV/bin/python" main.py --listen "$H3_HOST" --port "$H3_PORT" --disable-auto-launch
     --output-directory "$H3_RUNTIME/output" --input-directory "$H3_RUNTIME/input" "${EXTRA[@]}")
cd "$H3_COMFY_DIR"
if [ $FG = 1 ]; then exec "${CMD[@]}"; fi

nohup "${CMD[@]}" > "$H3_LOG" 2>&1 &
echo $! > "$H3_PIDFILE"
h3_log "started pid $(cat "$H3_PIDFILE"), log $H3_LOG; waiting for the API"
for _ in $(seq 1 180); do
  if curl -fs "http://$H3_HOST:$H3_PORT/system_stats" >/dev/null 2>&1; then
    h3_log "ready: http://$H3_HOST:$H3_PORT"; exit 0
  fi
  kill -0 "$(cat "$H3_PIDFILE")" 2>/dev/null || { h3_log "ComfyUI exited; tail of log:"; tail -30 "$H3_LOG"; exit 1; }
  sleep 1
done
h3_log "timed out waiting for the API; see $H3_LOG"; exit 1
