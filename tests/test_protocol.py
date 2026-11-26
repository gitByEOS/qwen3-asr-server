"""L4 协议层：EnhanceState 与 TranscribeResult。"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.protocol import EnhanceState, SpeechEnhancer, TranscribeResult


class TestEnhanceState(unittest.TestCase):
    def test_default_is_on(self) -> None:
        self.assertEqual(EnhanceState.parse(None), EnhanceState.ON)
        self.assertEqual(EnhanceState.parse(""), EnhanceState.ON)

    def test_on_and_off(self) -> None:
        self.assertEqual(EnhanceState.parse("on"), EnhanceState.ON)
        self.assertEqual(EnhanceState.parse("off"), EnhanceState.OFF)

    def test_reject_unknown(self) -> None:
        with self.assertRaises(ValueError):
            EnhanceState.parse("maybe")


class TestTranscribeResult(unittest.TestCase):
    def test_has_no_timeline_fields(self) -> None:
        result = TranscribeResult(text="你好", language="zh", enhance=EnhanceState.ON)
        self.assertEqual(result.text, "你好")
        self.assertFalse(hasattr(result, "segments"))
        self.assertFalse(hasattr(result, "srt"))


class TestSpeechEnhancerProtocol(unittest.TestCase):
    def test_prepare_signature(self) -> None:
        class Dummy:
            def prepare(self, audio_path: Path, enhance: EnhanceState) -> list[Path]:
                return [audio_path]

        self.assertIsInstance(Dummy(), SpeechEnhancer)


if __name__ == "__main__":
    unittest.main()
