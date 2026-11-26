"""转写结果。不含时间轴。"""

from __future__ import annotations

from dataclasses import dataclass

from src.protocol.states import EnhanceState


@dataclass(frozen=True)
class TranscribeResult:
    text: str
    language: str
    enhance: EnhanceState
