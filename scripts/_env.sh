# shellcheck shell=bash
# Shared settings for every script in scripts/. Source it, don't run it.
# Override any value in config/h3gen.env (copy config/h3gen.env.example) or in the environment.

H3_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$H3_REPO/config/h3gen.env" ]; then
  # shellcheck disable=SC1091
  . "$H3_REPO/config/h3gen.env"
fi

# Where ComfyUI, its venv, downloaded models and logs live. Keep it on the Linux filesystem (not /mnt/c):
# venvs and multi-GB safetensors are much slower across the 9P bridge.
H3_RUNTIME="${H3_RUNTIME:-$HOME/h3-video-gen-runtime}"
H3_COMFY_DIR="$H3_RUNTIME/ComfyUI"
H3_VENV="$H3_COMFY_DIR/.venv"
H3_MODELS="$H3_RUNTIME/models"
H3_LOG="$H3_RUNTIME/comfyui.log"
H3_PIDFILE="$H3_RUNTIME/comfyui.pid"

H3_HOST="${H3_HOST:-127.0.0.1}"
H3_PORT="${H3_PORT:-8190}"

# Optional existing model folder to reuse read-only (ComfyUI layout: diffusion_models/, text_encoders/, vae/, loras/).
# Files found here are not downloaded again. Empty (the default) disables it; set it in config/h3gen.env.
H3_SHARED_MODELS="${H3_SHARED_MODELS:-}"

# Pinned upstream versions (bump deliberately; record the bump in work-notes/).
COMFY_REPO="${COMFY_REPO:-https://github.com/comfyanonymous/ComfyUI.git}"
COMFY_REF="${COMFY_REF:-v0.46.2}"
PIFLOW_REPO="${PIFLOW_REPO:-https://github.com/Lakonik/ComfyUI-piFlow.git}"
PIFLOW_REF="${PIFLOW_REF:-bcb6ffb8ff}"   # v1.4.0, "Add pi-H3 workflows and docs"
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu130}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

h3_log() { printf '[h3] %s\n' "$*" >&2; }
