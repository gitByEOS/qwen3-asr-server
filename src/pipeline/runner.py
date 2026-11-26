"""L2：校验开关 → 预处理 → 转写。"""

from __future__ import annotations

import tempfile
import threading
import wave
from collections.abc import Callable
from pathlib import Path

from src.protocol.engines import AsrEngine, SpeechEnhancer
from src.protocol.errors import BusyError
from src.protocol.results import TranscribeResult
from src.protocol.states import EnhanceState

IDLE_TICKS = 5
Progress = Callable[[str], None]


def piece_seconds(path: Path) -> str:
    try:
        with wave.open(str(path), "rb") as source:
            rate = source.getframerate()
            seconds = source.getnframes() / rate if rate else 0
    except (wave.Error, EOFError, FileNotFoundError, OSError):
        seconds = 0
    rounded = round(seconds, 1)
    if abs(rounded - round(rounded)) < 0.05:
        return f"{rounded:.0f}"
    return f"{rounded:.1f}"


def _drop_renders(pieces: list[Path], source: Path) -> None:
    root = Path(tempfile.gettempdir()).resolve()
    source_resolved = source.resolve()
    for piece in pieces:
        resolved = piece.resolve()
        if resolved == source_resolved or root not in resolved.parents:
            continue
        piece.unlink(missing_ok=True)


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
        pieces: list[Path] = []
        try:
            notify("开始转写")
            notify("人声增强" if state is EnhanceState.ON else "音频直通")
            notify("转码中")
            pieces = self._enhancer.prepare(Path(audio_path), state)
            total = len(pieces)
            notify("整段解析" if total == 1 else f"切成 {total} 段")
            partial = on_partial or (lambda _text: None)
            texts: list[str] = []
            detected = language
            for index, piece in enumerate(pieces, start=1):
                prefix = "".join(texts)

                def emit(chunk: str, prefix: str = prefix) -> None:
                    shown = prefix + chunk
                    if shown:
                        partial(shown)

                def report(message: str, index: int = index, total: int = total) -> None:
                    plain = {"加载模型": "加载模型...", "模型已加载": "模型已加载"}
                    if message in plain:
                        notify(plain[message])
                        return
                    notify(f"第 {index}/{total} 段，{message}")

                notify(f"开始处理第 {index}/{total} 段，时长 {piece_seconds(piece)} s")
                text, detected = self._engine.transcribe(
                    piece, language, on_partial=emit, on_status=report
                )
                texts.append(text)
                if texts:
                    partial("".join(texts))
            text = "".join(texts)
            notify(text)
            return TranscribeResult(text=text, language=detected, enhance=state)
        except Exception as error:
            notify(str(error))
            raise
        finally:
            _drop_renders(pieces, Path(audio_path))
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
