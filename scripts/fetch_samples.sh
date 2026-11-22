#!/usr/bin/env bash
# Fetch the reference images used by the official pi-H3 Space examples into samples/images/ (gitignored:
# third-party images, not redistributed in this repo). Verified by sha256 (the HF LFS object ids).
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
BASE="https://huggingface.co/spaces/Lakonik/pi-H3/resolve/main/demo/examples/minimax_h3"
DEST="$H3_REPO/samples/images"
mkdir -p "$DEST"
while read -r sha name; do
  f="$DEST/$name"
  if [ -f "$f" ] && echo "$sha  $f" | sha256sum -c --status; then h3_log "ok    $name"; continue; fi
  h3_log "fetch $name"
  curl -fsSL --retry 3 -o "$f" "$BASE/$name"
  echo "$sha  $f" | sha256sum -c --status || { h3_log "sha256 mismatch: $name"; exit 1; }
done <<'EOF'
67d196818277d4895ed61b9e5675a5787e5588ad499a951a243b9067130a82a0 distracted_boyfriend.webp
3c2e16dcc05c27c6efb77d46f7e5aaff35a19e8add483a5890e8ecbf106d3706 woman_cat_meme_first.webp
113b1246c0f943eff208260ceb718f641ca85e9cbd0f0096d388c8b826fb7060 woman_cat_meme_last.webp
EOF
