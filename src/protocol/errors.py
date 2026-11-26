"""跨层错误。"""


class OfflineError(Exception):
    """本地模型缓存缺失。"""


class BusyError(Exception):
    """已有转写在进行。"""
