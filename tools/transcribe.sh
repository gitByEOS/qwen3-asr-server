#!/bin/bash
# 单次转写，不启动服务；保留调用者目录以解析输入路径
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${ROOT}/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export QWEN_ASR_BACKEND="${QWEN_ASR_BACKEND:-auto}"
if [[ -z "${QWEN_ASR_MODEL:-}" ]]; then
  if [[ "$QWEN_ASR_BACKEND" == "mlx" ]] || \
     [[ "$QWEN_ASR_BACKEND" == "auto" && "$(uname -s)-$(uname -m)" == "Darwin-arm64" ]]; then
    export QWEN_ASR_MODEL="${ROOT}/models/Qwen3-ASR-0.6B-MLX-4bit"
  else
    export QWEN_ASR_MODEL="${ROOT}/models/Qwen3-ASR-0.6B"
  fi
fi

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi
exec "$PYTHON" -B -m src.cli "$@"
