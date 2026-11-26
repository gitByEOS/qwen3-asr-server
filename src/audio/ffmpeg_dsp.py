"""一次 ffmpeg：转码，再按 EnhanceState 查滤镜表。缺 ffmpeg 时 wav 可直通。"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from src.protocol.errors import MissingDependencyError
from src.protocol.states import EnhanceState
from src.runtime.ffmpeg import is_ffmpeg_ready

FILTERS = {
    EnhanceState.OFF: (),
    EnhanceState.ON: ("highpass=f=80", "afftdn=nf=-25"),
}

WAV_SUFFIXES = {".wav", ".wave"}


def ffmpeg_args(source: Path, destination: Path, enhance: EnhanceState) -> list[str]:
    args = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
    ]
    filters = FILTERS[enhance]
    if filters:
        args.extend(["-af", ",".join(filters)])
    args.append(str(destination))
    return args


class FfmpegDspEnhancer:
    def prepare(self, audio_path: Path, enhance: EnhanceState) -> Path:
        source = Path(audio_path)
        if is_ffmpeg_ready():
            return self._run_ffmpeg(source, enhance)
        if enhance is EnhanceState.ON:
            raise MissingDependencyError("人声增强需要 ffmpeg")
        if source.suffix.lower() not in WAV_SUFFIXES:
            raise MissingDependencyError("非 wav 需要 ffmpeg")
        return source

    def _run_ffmpeg(self, source: Path, enhance: EnhanceState) -> Path:
        fd, name = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        destination = Path(name)
        command = ffmpeg_args(source, destination, enhance)
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "ffmpeg 转码失败")
        return destination
