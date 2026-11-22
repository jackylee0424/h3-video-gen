#!/usr/bin/env bash
# Download the pi-H3 DWD model set (ComfyUI / INT8 ConvRot) into $H3_RUNTIME/models. A file is skipped when it
# (or an accepted alternative) already exists there or in $H3_SHARED_MODELS. Resumable; sizes checked vs the HF API.
#
#   bash scripts/download_models.sh                    # profile "minimal" (default): 2-step adapter only
#   bash scripts/download_models.sh --profile full     # adds the 4-step adapter (+2.2 GB)
#   bash scripts/download_models.sh --dry-run          # show what would be fetched, download nothing
#
# Sizes (fresh machine): minimal ~42.3 GB, full ~44.5 GB. See docs/models.md.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_env.sh"

DRY=0; PROFILE="${H3_PROFILE:-minimal}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --profile) PROFILE="$2"; shift ;;
    --profile=*) PROFILE="${1#*=}" ;;
    *) h3_log "unknown argument: $1"; exit 2 ;;
  esac
  shift
done
case "$PROFILE" in minimal|full) ;; *) h3_log "profile must be minimal or full"; exit 2 ;; esac

# profile  target(type/file)  repo  path-in-repo  [alternative files that satisfy this slot, comma-separated]
MODELS=(
  "minimal diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors Comfy-Org/MiniMax-H3 diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors"
  "minimal text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors Comfy-Org/MiniMax-H3 text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
  "minimal vae/minimax_h3_video_vae_int8_convrot.safetensors Comfy-Org/MiniMax-H3 vae/minimax_h3_video_vae_int8_convrot.safetensors vae/minimax_h3_video_vae_fp16.safetensors"
  "minimal vae/minimax_h3_audio_vae_fp32.safetensors Comfy-Org/MiniMax-H3 vae/minimax_h3_audio_vae_fp32.safetensors"
  "minimal loras/pi_h3_2step_dwd_adapter_int8_convrot.safetensors Lakonik/pi-H3 pi_h3_2step_dwd_adapter_int8_convrot.safetensors"
  "full    loras/pi_h3_4step_dwd_adapter_int8_convrot.safetensors Lakonik/pi-H3 pi_h3_4step_dwd_adapter_int8_convrot.safetensors"
)
# More files (e.g. the w6a8 transformer, see docs/models.md): EXTRA_MODELS="minimal type/file repo path;..."
if [ -n "${EXTRA_MODELS:-}" ]; then IFS=';' read -r -a extra <<< "$EXTRA_MODELS"; MODELS+=("${extra[@]}"); fi

remote_size() {  # LFS size from the HF tree API ("" if unavailable)
  local repo=$1 path=$2 dir; dir=$(dirname "$path"); [ "$dir" = . ] && dir=""
  curl -fsSL "https://huggingface.co/api/models/$repo/tree/main/$dir" 2>/dev/null \
    | python3 -c "import json,sys; p=sys.argv[1]; print(next((f['size'] for f in json.load(sys.stdin) if f['path']==p), ''))" "$path" \
    || true
}
find_model() {  # first existing path for a relative model path, searching our folder then the shared one
  local rel=$1 base
  for base in "$H3_MODELS" ${H3_SHARED_MODELS:+"$H3_SHARED_MODELS"}; do
    if [ -f "$base/$rel" ]; then echo "$base/$rel"; return 0; fi
  done
  return 1
}

fail=0
for entry in "${MODELS[@]}"; do
  read -r prof rel repo path alts <<< "$entry"
  if [ "$prof" = full ] && [ "$PROFILE" != full ]; then
    if found=$(find_model "$rel"); then h3_log "ok      $rel  (optional, present: $found)"; else h3_log "skip    $rel  (profile full only)"; fi
    continue
  fi
  want=$(remote_size "$repo" "$path")
  if found=$(find_model "$rel"); then
    have=$(stat -c %s "$found")
    if [ -n "$want" ] && [ "$have" != "$want" ]; then
      h3_log "SIZE MISMATCH $found ($have != $want); delete it and re-run"; fail=1
    else
      h3_log "ok      $rel  ($((have / 1000000)) MB, $found)"
    fi
    continue
  fi
  alt_found=""
  if [ -n "${alts:-}" ]; then
    IFS=',' read -r -a alt_list <<< "$alts"
    for a in "${alt_list[@]}"; do if f=$(find_model "$a"); then alt_found=$f; break; fi; done
  fi
  if [ -n "$alt_found" ]; then
    h3_log "ok      $rel  (using alternative $alt_found)"
    continue
  fi
  dest="$H3_MODELS/$rel"
  h3_log "fetch   $rel  ($(( ${want:-0} / 1000000 )) MB) from $repo"
  [ $DRY = 1 ] && continue
  mkdir -p "$(dirname "$dest")"
  curl -fL --retry 5 --retry-delay 5 -C - -o "$dest.part" "https://huggingface.co/$repo/resolve/main/$path"
  have=$(stat -c %s "$dest.part")
  if [ -n "$want" ] && [ "$have" != "$want" ]; then h3_log "size mismatch after download: $dest.part"; fail=1; continue; fi
  mv "$dest.part" "$dest"
done
exit $fail
