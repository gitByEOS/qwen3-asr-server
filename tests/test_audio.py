"""L3 滤镜表：on 接高通降噪，off 只转码。"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.audio.ffmpeg_dsp import FILTERS, ffmpeg_args
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


if __name__ == "__main__":
    unittest.main()
