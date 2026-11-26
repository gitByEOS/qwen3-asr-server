"""L2：校验开关 → 预处理 → 转写。"""

from __future__ import annotations

import threading
from pathlib import Path

from src.protocol.engines import AsrEngine, SpeechEnhancer
from src.protocol.errors import BusyError
from src.protocol.results import TranscribeResult
from src.protocol.states import EnhanceState


class Pipeline:
    def __init__(self, enhancer: SpeechEnhancer, engine: AsrEngine):
        self._enhancer = enhancer
        self._engine = engine
        self._lock = threading.Lock()

    def run(
        self,
        audio_path: Path,
        language: str = "auto",
        enhance: str | EnhanceState | None = None,
    ) -> TranscribeResult:
        state = enhance if isinstance(enhance, EnhanceState) else EnhanceState.parse(enhance)
        if not self._lock.acquire(blocking=False):
            raise BusyError("转写进行中")
        try:
            prepared = self._enhancer.prepare(Path(audio_path), state)
            text, detected = self._engine.transcribe(prepared, language)
            return TranscribeResult(text=text, language=detected, enhance=state)
        finally:
            self._lock.release()
