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
PIFLOW_REF="${PIFLOW_REF:-4355cc4794}"   # v1.4.2 + #44 (DWD head norm_out casts without dynamic VRAM)
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu130}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

# Optional Spark-Attn (Spark-H3 prebuilt release, Linux, CUDA 13.0). Installed by `setup.sh --spark` or H3_SPARK=1.
# One archive per GPU architecture; the sha256 values are from the release's SHA256SUMS.txt.
H3_SPARK="${H3_SPARK:-0}"
SPARK_VERSION="${SPARK_VERSION:-0.2.0}"
SPARK_URL_BASE="${SPARK_URL_BASE:-https://github.com/zechengtang/Spark-H3/releases/download/comfyui-v$SPARK_VERSION}"
SPARK_SHA256_sm120="b51a3ab20c6e677de67bfc3693727ff3789c9d2077680b4ff540d5766593858d"
SPARK_SHA256_sm89="ad03aef0d7adda50b059f1348c4c54c9beb23c3b4e894fe87e398fcc2346a99f"
SPARK_SHA256_sm86="8997f751296d1ff6c032125f2ce2fbc45a776bec5ac8cf40d5c30f3a6ac14a02"

h3_log() { printf '[h3] %s\n' "$*" >&2; }
