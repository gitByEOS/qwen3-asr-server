"""Qwen3-ASR 文本引擎。启动不加载，缺缓存抛 OfflineError。"""

from __future__ import annotations

import os
from pathlib import Path

from src.protocol.errors import MissingDependencyError, OfflineError

DEFAULT_MODEL_ID = "Qwen/Qwen3-ASR-0.6B"


def resolve_model_id() -> str:
    return os.environ.get("QWEN_ASR_MODEL") or DEFAULT_MODEL_ID


def load_qwen_from_cache(model_id: str):
    """只读本地缓存。"""
    try:
        from qwen_asr import Qwen3ASRModel
    except ImportError as error:
        raise MissingDependencyError("需要 qwen-asr") from error
    try:
        return Qwen3ASRModel.from_pretrained(model_id, local_files_only=True)
    except ImportError as error:
        raise MissingDependencyError("需要 qwen-asr 依赖") from error
    except Exception as error:
        raise OfflineError("离线：本地模型缓存缺失") from error


def extract_text(raw) -> str:
    if raw is None:
        return ""
    if hasattr(raw, "text"):
        return str(raw.text)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return "".join(extract_text(item) for item in raw)
    return str(raw)


class QwenAsrEngine:
    def __init__(self, model_id: str | None = None, load_model=load_qwen_from_cache):
        self.model_id = model_id or resolve_model_id()
        self._load_model = load_model
        self.model = None
        self.load_count = 0

    def transcribe(self, audio_path: Path, language: str = "auto") -> tuple[str, str]:
        if self.model is None:
            self.model = self._load_model(self.model_id)
            self.load_count += 1
        raw = self.model.transcribe(str(audio_path), language=language)
        return extract_text(raw), language
