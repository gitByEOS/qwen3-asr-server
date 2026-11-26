"""L5 引擎：可注入替身，启动不加载。"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.asr.qwen_engine import QwenAsrEngine, extract_text
from src.protocol.errors import OfflineError
from tests.fakes import FakeLoader, MissingCacheLoader


class TestExtractText(unittest.TestCase):
    def test_object_text(self) -> None:
        self.assertEqual(extract_text(type("Raw", (), {"text": "你好"})()), "你好")


class TestQwenAsrEngine(unittest.TestCase):
    def test_init_does_not_load(self) -> None:
        loader = FakeLoader()
        engine = QwenAsrEngine(load_model=loader)
        self.assertEqual(engine.load_count, 0)
        self.assertEqual(loader.calls, 0)

    def test_transcribe_loads_once(self) -> None:
        loader = FakeLoader()
        engine = QwenAsrEngine(load_model=loader)
        text, language = engine.transcribe(Path("a.wav"), "zh")
        engine.transcribe(Path("b.wav"), "zh")
        self.assertEqual(text, "你好")
        self.assertEqual(language, "zh")
        self.assertEqual(engine.load_count, 1)
        self.assertEqual(loader.calls, 1)
        self.assertEqual(loader.network, 0)

    def test_missing_cache_is_offline(self) -> None:
        engine = QwenAsrEngine(load_model=MissingCacheLoader())
        with self.assertRaises(OfflineError):
            engine.transcribe(Path("a.wav"), "zh")


if __name__ == "__main__":
    unittest.main()
