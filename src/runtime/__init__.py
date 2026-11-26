"""L6 运行时：离线开关与 ffmpeg 探活。"""

from src.runtime.ffmpeg import ffmpeg_path, is_ffmpeg_ready
from src.runtime.offline import enable_offline_mode, is_offline

__all__ = [
    "enable_offline_mode",
    "ffmpeg_path",
    "is_ffmpeg_ready",
    "is_offline",
]
