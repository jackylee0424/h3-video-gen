#!/usr/bin/env bash
# One-screen health check for agents: runtime, models, server, GPU. Exit 0 only if ready to generate.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
ok=1
echo "runtime:  $H3_RUNTIME"
if [ -f "$H3_RUNTIME/versions.txt" ]; then sed 's/^/  /' "$H3_RUNTIME/versions.txt"; else echo "  NOT SET UP (bash scripts/setup.sh)"; ok=0; fi
echo "models:"
bash "$H3_REPO/scripts/download_models.sh" --dry-run 2>&1 | sed 's/^\[h3\] /  /'
bash "$H3_REPO/scripts/download_models.sh" --dry-run 2>&1 | grep -q 'fetch\|MISMATCH' && ok=0
if curl -fs "http://$H3_HOST:$H3_PORT/system_stats" >/dev/null 2>&1; then
  echo "server:   up  http://$H3_HOST:$H3_PORT"
else
  echo "server:   down (bash scripts/serve.sh)"; ok=0
fi
echo "gpu:      $(nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader)"
[ $ok = 1 ] && echo "READY" || echo "NOT READY"
[ $ok = 1 ]
