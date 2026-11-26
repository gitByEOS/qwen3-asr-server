"""跨层错误。"""


class OfflineError(Exception):
    """本地模型缓存缺失。"""


class BusyError(Exception):
    """已有转写在进行。"""


class MissingDependencyError(Exception):
    """缺 ffmpeg / qwen-asr 等，进程继续、请求失败。"""
