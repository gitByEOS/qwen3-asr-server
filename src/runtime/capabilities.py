"""能力探测：只查是否存在，不加载模型。"""

from __future__ import annotations

import importlib.util

from src.runtime.ffmpeg import is_ffmpeg_ready


def is_qwen_asr_ready() -> bool:
    return importlib.util.find_spec("qwen_asr") is not None


def is_torch_ready() -> bool:
    return importlib.util.find_spec("torch") is not None


def probe() -> dict[str, bool]:
    return {
        "ffmpeg": is_ffmpeg_ready(),
        "qwen_asr": is_qwen_asr_ready(),
        "torch": is_torch_ready(),
    }


def missing_of(capabilities: dict[str, bool]) -> list[str]:
    return [name for name, ready in capabilities.items() if not ready]
