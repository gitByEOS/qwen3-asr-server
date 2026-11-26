#!/usr/bin/env bash
# 用 uv + 清华源装包，用魔搭拉 Qwen3-ASR-0.6B。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv"
BIN="$ROOT/bin"
MODEL_DIR="$ROOT/models/Qwen3-ASR-0.6B"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
FFMPEG_STATIC_TAG="b6.1.1"
# 统一解释器，避免 Intel Mac 使用 Python 3.13 时没有可用的 torch 轮子
PYTHON_VERSION="3.12"
export PATH="${BIN}:/opt/homebrew/bin:/usr/local/bin:${PATH}"

log() { echo "[setup] $*"; }
fail() { echo "$*" >&2; exit 1; }

base_python() {
  if command -v "python${PYTHON_VERSION}" >/dev/null; then
    command -v "python${PYTHON_VERSION}"
    return
  fi
  uv python install "$PYTHON_VERSION" >/dev/null || return "$?"
  uv python find "$PYTHON_VERSION"
}

ffmpeg_asset() {
  case "$(uname -s)-$(uname -m)" in
    Darwin-x86_64) echo "ffmpeg-darwin-x64.gz" ;;
    Darwin-arm64) echo "ffmpeg-darwin-arm64.gz" ;;
    Linux-x86_64) echo "ffmpeg-linux-x64.gz" ;;
    Linux-aarch64) echo "ffmpeg-linux-arm64.gz" ;;
    *) echo "" ;;
  esac
}

install_ffmpeg_static() {
  local asset
  asset="$(ffmpeg_asset)"
  if [[ -z "$asset" ]]; then
    echo "没有可用的静态 ffmpeg" >&2
    exit 1
  fi
  log "下载静态 ffmpeg ${asset}"
  mkdir -p "$BIN"
  curl -fL "https://github.com/eugeneware/ffmpeg-static/releases/download/${FFMPEG_STATIC_TAG}/${asset}" -o "$BIN/ffmpeg.gz"
  gzip -df "$BIN/ffmpeg.gz"
  chmod +x "$BIN/ffmpeg"
}

ensure_ffmpeg() {
  if command -v ffmpeg >/dev/null; then
    return
  fi
  install_ffmpeg_static
}

check_python() {
  [[ -x "$VENV/bin/python" ]] || fail "已有 .venv 不完整，已保留：${VENV}；请先移走该目录，再运行 ./tools/setup.sh"
  local version
  version="$("$VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" || fail "无法运行 .venv 中的解释器，已保留：${VENV}；请先移走该目录，再运行 ./tools/setup.sh"
  [[ "$version" == "$PYTHON_VERSION" ]] || fail "已有 .venv 使用 Python ${version}，需要 Python ${PYTHON_VERSION}，已保留：${VENV}；请先移走该目录，再运行 ./tools/setup.sh"
}

ensure_venv() {
  if [[ -e "$VENV" || -L "$VENV" ]]; then
    check_python
    return
  fi
  local python
  python="$(base_python)"
  log "使用 Python ${PYTHON_VERSION} 创建 .venv"
  uv venv "$VENV" --python "$python"
  check_python
}

pip_install() {
  uv pip install --python "$VENV/bin/python" --default-index "$PIP_INDEX_URL" "$@"
}

install_python_packages() {
  log "清华源安装 torch qwen-asr modelscope"
  pip_install torch qwen-asr modelscope "numpy<2" "numba<0.61"
}

ensure_model() {
  if [[ -f "$MODEL_DIR/config.json" ]]; then
    return
  fi
  log "魔搭下载 Qwen3-ASR-0.6B"
  mkdir -p "$MODEL_DIR"
  "$VENV/bin/python" - "$MODEL_DIR" <<'PY'
from pathlib import Path
import sys

from modelscope.hub.snapshot_download import snapshot_download

destination = Path(sys.argv[1])
snapshot_download("Qwen/Qwen3-ASR-0.6B", local_dir=str(destination))
print("模型已落到", destination)
PY
}

run_check() {
  [[ -e "$VENV" || -L "$VENV" ]] || fail "尚未安装，请先运行 ./tools/setup.sh"
  check_python
  PYTHONPATH="$ROOT" "$VENV/bin/python" - <<'PY'
from src.runtime.capabilities import missing_of, probe

capabilities = probe()
print(capabilities)
missing = missing_of(capabilities)
if missing:
    raise SystemExit("缺少：" + "、".join(missing))
print("完备")
PY
}

case "${1:-}" in
  --check)
    run_check
    ;;
  "")
    command -v uv >/dev/null || fail "需要 uv，请先安装 uv 后再运行 ./tools/setup.sh"
    ensure_venv
    ensure_ffmpeg
    install_python_packages
    ensure_model
    run_check
    ;;
  *)
    echo "用法: $0 [--check]" >&2
    exit 2
    ;;
esac
