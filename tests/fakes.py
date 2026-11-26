"""测试替身。不加载真实模型。"""

from __future__ import annotations

from pathlib import Path

from src.protocol.errors import OfflineError
from src.protocol.states import EnhanceState


class FakeModel:
    def transcribe(self, audio_path: str, language: str = "auto"):
        return type("Raw", (), {"text": "你好"})()


class FakeLoader:
    def __init__(self) -> None:
        self.calls = 0
        self.network = 0

    def __call__(self, model_id: str):
        self.calls += 1
        return FakeModel()


class MissingCacheLoader:
    def __init__(self) -> None:
        self.network = 0

    def __call__(self, model_id: str):
        raise OfflineError("本地模型缓存缺失")


class FakeEnhancer:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, EnhanceState]] = []

    def prepare(self, audio_path: Path, enhance: EnhanceState) -> Path:
        self.calls.append((audio_path, enhance))
        return audio_path
