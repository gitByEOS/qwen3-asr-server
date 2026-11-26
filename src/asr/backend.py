"""按平台选择 ASR 推理后端。"""

from __future__ import annotations

import os
import platform

BACKEND_AUTO = "auto"
BACKEND_MLX = "mlx"
BACKEND_TORCH = "torch"
BACKENDS = (BACKEND_AUTO, BACKEND_MLX, BACKEND_TORCH)


def is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def resolve_backend(value: str | None = None) -> str:
    requested = (value or os.environ.get("QWEN_ASR_BACKEND") or BACKEND_AUTO).lower()
    if requested not in BACKENDS:
        raise ValueError("QWEN_ASR_BACKEND 只接受 auto、mlx、torch")
    if requested == BACKEND_AUTO:
        return BACKEND_MLX if is_apple_silicon() else BACKEND_TORCH
    return requested


def create_engine(backend: str | None = None):
    selected = resolve_backend(backend)
    if selected == BACKEND_MLX:
        from src.asr.mlx_engine import MlxQwenAsrEngine

        return selected, MlxQwenAsrEngine()
    from src.asr.qwen_engine import QwenAsrEngine

    return selected, QwenAsrEngine()
