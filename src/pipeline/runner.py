"""L2：校验开关 → 预处理 → 转写。"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from src.protocol.engines import AsrEngine, SpeechEnhancer
from src.protocol.errors import BusyError
from src.protocol.results import TranscribeResult
from src.protocol.states import EnhanceState

IDLE_TICKS = 5
Progress = Callable[[str], None]


class Pipeline:
    def __init__(self, enhancer: SpeechEnhancer, engine: AsrEngine):
        self._enhancer = enhancer
        self._engine = engine
        self._lock = threading.Lock()
        self._idle_ticks = 0

    def run(
        self,
        audio_path: Path,
        language: str = "auto",
        enhance: str | EnhanceState | None = None,
        on_progress: Progress | None = None,
        on_partial: Progress | None = None,
    ) -> TranscribeResult:
        state = enhance if isinstance(enhance, EnhanceState) else EnhanceState.parse(enhance)
        if not self._lock.acquire(blocking=False):
            raise BusyError("转写进行中")
        notify = on_progress or (lambda _message: None)
        self._idle_ticks = 0
        try:
            notify("开始转写")
            notify("人声增强" if state is EnhanceState.ON else "音频直通")
            prepared = self._enhancer.prepare(Path(audio_path), state)
            if getattr(self._engine, "model", None) is None:
                notify("冷启动加载模型")
            else:
                notify("模型已在内存")
            notify("转写中")
            partial = on_partial or (lambda _text: None)
            text, detected = self._engine.transcribe(prepared, language, on_partial=partial)
            notify(text)
            return TranscribeResult(text=text, language=detected, enhance=state)
        except Exception as error:
            notify(str(error))
            raise
        finally:
            self._lock.release()

    def is_busy(self) -> bool:
        return self._lock.locked()

    def heartbeat(self) -> bool:
        if self._lock.locked():
            self._idle_ticks = 0
            return False
        if getattr(self._engine, "model", None) is None:
            self._idle_ticks = 0
            return False
        self._idle_ticks += 1
        if self._idle_ticks < IDLE_TICKS:
            return False
        self._engine.release()
        self._idle_ticks = 0
        return True
