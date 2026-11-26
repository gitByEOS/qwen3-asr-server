"""L5 引擎：可注入替身，启动不加载。"""

from __future__ import annotations

import unittest
from pathlib import Path

import sys
from unittest.mock import patch

from src.asr.qwen_engine import QwenAsrEngine, extract_text, load_qwen_from_cache
from src.protocol.errors import MissingDependencyError, OfflineError
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

    def test_missing_qwen_asr_is_dependency(self) -> None:
        with patch.dict(sys.modules, {"qwen_asr": None}):
            with self.assertRaises(MissingDependencyError):
                load_qwen_from_cache("Qwen/Qwen3-ASR-0.6B")


if __name__ == "__main__":
    unittest.main()
