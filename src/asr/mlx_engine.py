"""Apple Silicon 上的 Qwen3-ASR MLX 文本引擎。"""

from __future__ import annotations

import gc
import os
from pathlib import Path

from src.protocol.errors import MissingDependencyError, OfflineError

DEFAULT_MLX_MODEL_ID = "aufklarer/Qwen3-ASR-0.6B-MLX-4bit"


def resolve_mlx_model_id() -> str:
    return os.environ.get("QWEN_ASR_MODEL") or DEFAULT_MLX_MODEL_ID


def load_mlx_from_cache(model_id: str):
    """只从 setup 已下载的本地目录加载 MLX 权重。"""
    model_path = Path(model_id).expanduser()
    if not model_path.is_dir() or not (model_path / "config.json").is_file():
        raise OfflineError("离线：本地 MLX 模型缓存缺失")
    try:
        from mlx_audio.stt import load
    except ImportError as error:
        raise MissingDependencyError("需要 Qwen3-ASR MLX 推理组件") from error
    try:
        return load(model_path)
    except ImportError as error:
        raise MissingDependencyError("需要 Qwen3-ASR MLX 推理组件") from error
    except Exception as error:
        raise OfflineError("离线：本地 MLX 模型加载失败") from error


def mlx_language(language: str | None) -> str | None:
    if language is None or language.strip() in ("", "auto"):
        return None
    aliases = {
        "zh": "Chinese",
        "en": "English",
        "yue": "Cantonese",
        "ja": "Japanese",
        "ko": "Korean",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
    }
    return aliases.get(language.lower(), language)


class MlxQwenAsrEngine:
    def __init__(self, model_id: str | None = None, load_model=load_mlx_from_cache):
        self.model_id = model_id or resolve_mlx_model_id()
        self._load_model = load_model
        self.model = None
        self.load_count = 0

    def transcribe(
        self,
        audio_path: Path,
        language: str = "auto",
        on_partial=None,
        on_status=None,
    ) -> tuple[str, str]:
        status = on_status or (lambda _message: None)
        if self.model is None:
            status("加载模型")
            self.model = self._load_model(self.model_id)
            self.load_count += 1
            status("模型已加载")

        selected_language = mlx_language(language)
        if on_partial is None:
            raw = self.model.generate(
                str(audio_path), language=selected_language, verbose=False
            )
            return str(getattr(raw, "text", raw)), str(
                getattr(raw, "language", "") or selected_language or language
            )

        pieces: list[str] = []
        detected = ""
        heard = False
        stream = self.model.generate(
            str(audio_path), language=selected_language, verbose=False, stream=True
        )
        for event in stream:
            piece = str(getattr(event, "text", "") or "")
            event_language = getattr(event, "language", "")
            if event_language:
                detected = str(event_language)
            if not piece:
                continue
            if not heard:
                heard = True
                status("正在出字...")
            pieces.append(piece)
            on_partial("".join(pieces))
        return "".join(pieces), detected or selected_language or language

    def release(self) -> None:
        self.model = None
        gc.collect()
        try:
            import mlx.core as mx

            mx.clear_cache()
        except ImportError:
            pass
