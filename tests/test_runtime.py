"""L6 运行时：离线环境与 ffmpeg 探活。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.runtime.ffmpeg import is_ffmpeg_ready
from src.runtime.offline import HF_OFFLINE_ENVS, enable_offline_mode, is_offline


class TestOffline(unittest.TestCase):
    def setUp(self) -> None:
        self.saved = {name: os.environ.get(name) for name in HF_OFFLINE_ENVS}

    def tearDown(self) -> None:
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_enable_sets_both_env(self) -> None:
        for name in HF_OFFLINE_ENVS:
            os.environ.pop(name, None)
        enable_offline_mode()
        self.assertTrue(is_offline())


class TestFfmpeg(unittest.TestCase):
    def test_missing_ffmpeg_is_not_ready(self) -> None:
        with patch("src.runtime.ffmpeg.shutil.which", return_value=None):
            self.assertFalse(is_ffmpeg_ready())

    def test_found_ffmpeg_is_ready(self) -> None:
        with patch("src.runtime.ffmpeg.shutil.which", return_value="/usr/bin/ffmpeg"):
            self.assertTrue(is_ffmpeg_ready())


if __name__ == "__main__":
    unittest.main()
