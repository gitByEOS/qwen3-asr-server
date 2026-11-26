#!/usr/bin/env bash
# 用 uv + 清华源装包，用魔搭下载对应平台的 Qwen3-ASR-0.6B。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv"
BIN="$ROOT/bin"
TORCH_MODEL_DIR="$ROOT/models/Qwen3-ASR-0.6B"
MLX_MODEL_DIR="$ROOT/models/Qwen3-ASR-0.6B-MLX-4bit"
TORCH_MODEL_ID="Qwen/Qwen3-ASR-0.6B"
MLX_MODEL_ID="aufklarer/Qwen3-ASR-0.6B-MLX-4bit"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
FFMPEG_STATIC_TAG="b6.1.1"
# 统一解释器，避免 Intel Mac 使用 Python 3.13 时没有可用的 torch 轮子
PYTHON_VERSION="3.12"
EXISTING_PYTHON3="$(command -v python3 || true)"
export PATH="${BIN}:/opt/homebrew/bin:/usr/local/bin:${PATH}"

log() { echo "[setup] $*"; }
fail() { echo "$*" >&2; exit 1; }

selected_backend() {
  case "${QWEN_ASR_BACKEND:-auto}" in
    mlx|torch) echo "${QWEN_ASR_BACKEND}" ;;
    auto)
      if [[ "$(uname -s)-$(uname -m)" == "Darwin-arm64" ]]; then
        echo "mlx"
      else
        echo "torch"
      fi
      ;;
    *)
      echo "QWEN_ASR_BACKEND 只接受 auto、mlx、torch" >&2
      return 2
      ;;
  esac
}

model_dir() {
  if [[ "$(selected_backend)" == "mlx" ]]; then
    echo "$MLX_MODEL_DIR"
  else
    echo "$TORCH_MODEL_DIR"
  fi
}

model_id() {
  if [[ "$(selected_backend)" == "mlx" ]]; then
    echo "$MLX_MODEL_ID"
  else
    echo "$TORCH_MODEL_ID"
  fi
}

python_at_least_312() {
  "$1" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' >/dev/null 2>&1
}

mlx_python() {
  local candidate path
  if [[ -n "$EXISTING_PYTHON3" ]] && python_at_least_312 "$EXISTING_PYTHON3"; then
    echo "$EXISTING_PYTHON3"
    return
  fi
  for candidate in python3.14 python3.13 python3.12; do
    path="$(command -v "$candidate" || true)"
    if [[ -n "$path" ]] && python_at_least_312 "$path"; then
      echo "$path"
      return
    fi
  done
  uv python install 3.12 >/dev/null
  uv python find 3.12
}

base_python() {
  if [[ "$(selected_backend)" == "mlx" ]]; then
    mlx_python
    return
  fi
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
  local version major minor
  version="$("$VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" || fail "无法运行 .venv 中的解释器，已保留：${VENV}；请先移走该目录，再运行 ./tools/setup.sh"
  if [[ "$(selected_backend)" == "mlx" ]]; then
    major="${version%%.*}"
    minor="${version#*.}"
    if (( major < 3 || (major == 3 && minor < 12) )); then
      fail "已有 .venv 使用 Python ${version}，Qwen3-ASR MLX 后端需要 Python ≥3.12，已保留：${VENV}；请先移走该目录，再运行 ./tools/setup.sh"
    fi
    return
  fi
  [[ "$version" == "$PYTHON_VERSION" ]] || fail "已有 .venv 使用 Python ${version}，torch 后端需要 Python ${PYTHON_VERSION}，已保留：${VENV}；请先移走该目录，再运行 ./tools/setup.sh"
}

ensure_venv() {
  if [[ -e "$VENV" || -L "$VENV" ]]; then
    check_python
    return
  fi
  local python version
  python="$(base_python)"
  version="$("$python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  log "使用 Python ${version} 创建 .venv"
  uv venv "$VENV" --python "$python"
  check_python
}

pip_install() {
  uv pip install --python "$VENV/bin/python" --default-index "$PIP_INDEX_URL" "$@"
}

install_python_packages() {
  if [[ "$(selected_backend)" == "mlx" ]]; then
    log "清华源安装 Qwen3-ASR MLX 推理组件"
    pip_install "mlx-audio[stt]==0.6.8" modelscope
  else
    log "清华源安装 torch qwen-asr modelscope"
    pip_install torch qwen-asr modelscope "numpy<2" "numba<0.61"
  fi
}

ensure_model() {
  local destination repo_id
  destination="$(model_dir)"
  repo_id="$(model_id)"
  if [[ ! -f "$destination/config.json" ]]; then
    log "魔搭下载 ${repo_id}"
    mkdir -p "$destination"
    "$VENV/bin/python" - "$destination" "$repo_id" <<'PY'
from pathlib import Path
import sys

from modelscope.hub.snapshot_download import snapshot_download

destination = Path(sys.argv[1])
snapshot_download(sys.argv[2], local_dir=str(destination))
print("模型已落到", destination)
PY
  fi
  if [[ "$(selected_backend)" == "mlx" && ! -f "$destination/preprocessor_config.json" ]]; then
    log "补 MLX Python 特征提取配置"
    cp "$ROOT/tools/mlx_preprocessor_config.json" "$destination/preprocessor_config.json"
  fi
}

run_check() {
  [[ -e "$VENV" || -L "$VENV" ]] || fail "尚未安装，请先运行 ./tools/setup.sh"
  check_python
  local backend destination
  backend="$(selected_backend)"
  destination="$(model_dir)"
  PYTHONPATH="$ROOT" "$VENV/bin/python" - "$backend" "$destination" <<'PY'
from pathlib import Path
import sys

from src.runtime.capabilities import missing_of, probe

backend, model_dir = sys.argv[1:]
capabilities = probe()
print(capabilities)
missing = missing_of(capabilities, backend)
if missing:
    raise SystemExit("缺少：" + "、".join(missing))
if not (Path(model_dir) / "config.json").is_file():
    raise SystemExit("缺少本地模型：" + model_dir)
if backend == "mlx" and not (Path(model_dir) / "preprocessor_config.json").is_file():
    raise SystemExit("MLX 模型缺少 preprocessor_config.json，请重新运行 setup")
print("后端：" + backend)
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
