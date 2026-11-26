#!/bin/bash
# 单次转写，不启动服务；保留调用者目录以解析输入路径
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${ROOT}/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export QWEN_ASR_MODEL="${QWEN_ASR_MODEL:-${ROOT}/models/Qwen3-ASR-0.6B}"

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi
exec "$PYTHON" -B -m src.cli "$@"
