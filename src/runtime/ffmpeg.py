"""ffmpeg 是否可用。不在探活时跑转码。"""

from __future__ import annotations

import shutil
from pathlib import Path


def ffmpeg_path() -> Path | None:
    found = shutil.which("ffmpeg")
    if not found:
        return None
    return Path(found)


def is_ffmpeg_ready() -> bool:
    return ffmpeg_path() is not None
