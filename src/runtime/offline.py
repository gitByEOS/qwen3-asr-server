"""离线：启动即切断 HuggingFace 网络。"""

from __future__ import annotations

import os

HF_OFFLINE_ENVS = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")


def enable_offline_mode() -> None:
    for name in HF_OFFLINE_ENVS:
        os.environ[name] = "1"


def is_offline() -> bool:
    return all(os.environ.get(name) == "1" for name in HF_OFFLINE_ENVS)
