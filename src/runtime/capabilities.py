"""能力探测：只查是否存在，不加载模型。"""

from __future__ import annotations

import importlib.util

from src.runtime.ffmpeg import is_ffmpeg_ready


def is_qwen_asr_ready() -> bool:
    return importlib.util.find_spec("qwen_asr") is not None


def is_torch_ready() -> bool:
    return importlib.util.find_spec("torch") is not None


def is_qwen_asr_mlx_ready() -> bool:
    """Qwen3-ASR MLX 后端所需组件是否齐全。"""
    return (
        importlib.util.find_spec("mlx") is not None
        and importlib.util.find_spec("mlx_audio") is not None
    )


def probe() -> dict[str, bool]:
    return {
        "ffmpeg": is_ffmpeg_ready(),
        "qwen_asr": is_qwen_asr_ready(),
        "torch": is_torch_ready(),
        "qwen_asr_mlx": is_qwen_asr_mlx_ready(),
    }


def missing_of(capabilities: dict[str, bool], backend: str = "torch") -> list[str]:
    required = ("ffmpeg", "qwen_asr_mlx") if backend == "mlx" else (
        "ffmpeg",
        "qwen_asr",
        "torch",
    )
    return [name for name in required if not capabilities.get(name, False)]
