#!/bin/bash
set -euo pipefail

WEB_PORT="${WEB_PORT:-11801}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONPATH="$SCRIPT_DIR"

python3 -m src
