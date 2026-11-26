"""增强开关：唯一状态 on / off。"""

from __future__ import annotations

from enum import Enum


class EnhanceState(str, Enum):
    ON = "on"
    OFF = "off"

    @classmethod
    def parse(cls, value: str | None) -> EnhanceState:
        """缺省为 on。其它字符串一律非法。"""
        if value is None or value == "":
            return cls.ON
        if value in (cls.ON.value, cls.OFF.value):
            return cls(value)
        raise ValueError("enhance 只接受 on 或 off")
