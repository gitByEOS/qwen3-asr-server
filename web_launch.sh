#!/bin/bash
set -euo pipefail

WEB_PORT="${WEB_PORT:-11801}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
export PATH="${SCRIPT_DIR}/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONPATH="$SCRIPT_DIR"
export QWEN_ASR_MODEL="${SCRIPT_DIR}/models/Qwen3-ASR-0.6B"

PYTHON="python3"
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON="$SCRIPT_DIR/.venv/bin/python"
fi
"$PYTHON" -m src
