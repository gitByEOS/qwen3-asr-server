"""L3 滤镜表：on 接高通降噪，off 只转码。"""

from __future__ import annotations

import unittest
from pathlib import Path

from unittest.mock import patch

from src.audio.ffmpeg_dsp import FILTERS, FfmpegDspEnhancer, ffmpeg_args
from src.protocol.errors import MissingDependencyError
from src.protocol.states import EnhanceState


class TestFilterTable(unittest.TestCase):
    def test_off_has_no_af(self) -> None:
        args = ffmpeg_args(Path("in.wav"), Path("out.wav"), EnhanceState.OFF)
        self.assertNotIn("-af", args)
        self.assertIn("16000", args)
        self.assertEqual(FILTERS[EnhanceState.OFF], ())

    def test_on_appends_highpass_and_denoise(self) -> None:
        args = ffmpeg_args(Path("in.wav"), Path("out.wav"), EnhanceState.ON)
        af = args[args.index("-af") + 1]
        self.assertIn("highpass=f=80", af)
        self.assertIn("afftdn=nf=-25", af)
        self.assertNotIn("ForcedAligner", af)


class TestMissingFfmpeg(unittest.TestCase):
    def test_wav_passthrough_when_ffmpeg_missing(self) -> None:
        path = Path("a.wav")
        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=False):
            self.assertEqual(FfmpegDspEnhancer().prepare(path, EnhanceState.OFF), path)

    def test_mp3_needs_ffmpeg(self) -> None:
        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=False):
            with self.assertRaises(MissingDependencyError):
                FfmpegDspEnhancer().prepare(Path("a.mp3"), EnhanceState.OFF)

    def test_enhance_on_needs_ffmpeg(self) -> None:
        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=False):
            with self.assertRaises(MissingDependencyError):
                FfmpegDspEnhancer().prepare(Path("a.wav"), EnhanceState.ON)


if __name__ == "__main__":
    unittest.main()
