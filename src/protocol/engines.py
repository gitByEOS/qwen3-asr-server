"""L3 / L5 可替换接口。"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from src.protocol.states import EnhanceState


@runtime_checkable
class SpeechEnhancer(Protocol):
    def prepare(self, audio_path: Path, enhance: EnhanceState) -> list[Path]:
        """解码为 16kHz 单声道，按静音切出人声段。"""
        ...


@runtime_checkable
class AsrEngine(Protocol):
    def transcribe(self, audio_path: Path, language: str) -> tuple[str, str]:
        """音频路径 → (text, language)。"""
        ...

    def release(self) -> None:
        """卸掉内存中的模型。"""
        ...
