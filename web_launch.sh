#!/bin/bash
set -euo pipefail

WEB_PORT="${WEB_PORT:-11868}"
export WEB_PORT
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
if lsof -nP -iTCP:"${WEB_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "端口 ${WEB_PORT} 已被占用" >&2
  lsof -nP -iTCP:"${WEB_PORT}" -sTCP:LISTEN >&2 || true
  exit 1
fi
"$PYTHON" -m src
