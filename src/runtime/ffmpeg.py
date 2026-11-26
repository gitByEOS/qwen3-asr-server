"""ffmpeg 是否可用。不在探活时跑转码。"""

from __future__ import annotations

import shutil
from pathlib import Path


EXTRA_BIN_DIRS = (
    Path(__file__).resolve().parents[2] / "bin",
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
)


def ffmpeg_path() -> Path | None:
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    for folder in EXTRA_BIN_DIRS:
        candidate = folder / "ffmpeg"
        if candidate.is_file():
            return candidate
    return None


def is_ffmpeg_ready() -> bool:
    return ffmpeg_path() is not None
