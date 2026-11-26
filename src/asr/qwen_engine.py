"""Qwen3-ASR 文本引擎。启动不加载，缺缓存抛 OfflineError。"""

from __future__ import annotations

import gc
import os
import threading
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
    text, _language = unpack_result(raw)
    return text


def unpack_result(raw) -> tuple[str, str]:
    if raw is None:
        return "", ""
    if isinstance(raw, list):
        texts = [unpack_result(item) for item in raw]
        return "".join(text for text, _language in texts), ",".join(
            language for _text, language in texts if language
        )
    if hasattr(raw, "text"):
        return str(raw.text), str(getattr(raw, "language", "") or "")
    if isinstance(raw, str):
        return raw, ""
    return str(raw), ""


ASR_TEXT_TAG = "<asr_text>"


def text_after_tag(raw: str) -> str:
    if ASR_TEXT_TAG not in raw:
        return ""
    return raw.split(ASR_TEXT_TAG, 1)[1].strip()


def forced_language(language: str | None) -> str | None:
    if language is None or language.strip() in ("", "auto"):
        return None
    return language


class QwenAsrEngine:
    def __init__(self, model_id: str | None = None, load_model=load_qwen_from_cache):
        self.model_id = model_id or resolve_model_id()
        self._load_model = load_model
        self.model = None
        self.load_count = 0

    def transcribe(self, audio_path: Path, language: str = "auto", on_partial=None) -> tuple[str, str]:
        if self.model is None:
            self.model = self._load_model(self.model_id)
            self.load_count += 1
        inner = getattr(self.model, "model", None)
        original = getattr(inner, "generate", None) if on_partial is not None else None
        if original is not None:
            inner.generate = self._streaming_generate(original, on_partial)
        try:
            raw = self.model.transcribe(str(audio_path), language=forced_language(language))
        finally:
            if original is not None:
                inner.generate = original
        text, detected = unpack_result(raw)
        return text, detected or language

    def _streaming_generate(self, original, on_partial):
        tokenizer = self.model.processor.tokenizer
        carried = {"text": ""}

        def wrapped(*args, **kwargs):
            from transformers import TextIteratorStreamer

            streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
            kwargs["streamer"] = streamer
            holder: dict = {}

            def run() -> None:
                try:
                    holder["out"] = original(*args, **kwargs)
                except Exception as error:
                    holder["error"] = error
                finally:
                    streamer.end()

            thread = threading.Thread(target=run)
            thread.start()
            pieces: list[str] = []
            for piece in streamer:
                pieces.append(piece)
                shown = carried["text"] + text_after_tag("".join(pieces))
                if shown:
                    on_partial(shown)
            thread.join()
            if "error" in holder:
                raise holder["error"]
            carried["text"] += text_after_tag("".join(pieces))
            return holder.get("out")

        return wrapped

    def release(self) -> None:
        self.model = None
        gc.collect()
