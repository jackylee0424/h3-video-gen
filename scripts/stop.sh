#!/usr/bin/env bash
# Stop the ComfyUI started by scripts/serve.sh and free the GPU.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
if [ -f "$H3_PIDFILE" ] && kill -0 "$(cat "$H3_PIDFILE")" 2>/dev/null; then
  kill "$(cat "$H3_PIDFILE")"
  for _ in $(seq 1 20); do kill -0 "$(cat "$H3_PIDFILE")" 2>/dev/null || break; sleep 1; done
  kill -9 "$(cat "$H3_PIDFILE")" 2>/dev/null || true
  h3_log "stopped"
else
  h3_log "not running"
fi
rm -f "$H3_PIDFILE"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
