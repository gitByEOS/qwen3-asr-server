"""L5 引擎：可注入替身，启动不加载。"""

from __future__ import annotations

import unittest
from pathlib import Path

import sys
from unittest.mock import patch

from src.asr.qwen_engine import (
    QwenAsrEngine,
    _quiet_generation,
    extract_text,
    forced_language,
    load_qwen_from_cache,
    text_after_tag,
)
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
        engine.release()
        self.assertIsNone(engine.model)

    def test_auto_does_not_force_language(self) -> None:
        seen: dict[str, str | None] = {}

        class Model:
            def transcribe(self, audio_path: str, language: str | None = None):
                seen["language"] = language
                return type("Raw", (), {"text": "你好", "language": "Chinese"})()

        engine = QwenAsrEngine(load_model=lambda model_id: Model())
        text, language = engine.transcribe(Path("a.wav"), "auto")
        self.assertIsNone(seen["language"])
        self.assertIsNone(forced_language("auto"))
        self.assertEqual(text, "你好")
        self.assertEqual(language, "Chinese")

    def test_ac_asr_017(self) -> None:
        self.assertEqual(text_after_tag("language Chinese"), "")
        self.assertEqual(text_after_tag("language Chinese<asr_text>你好"), "你好")

    def test_greedy_drops_unused_temperature(self) -> None:
        class OuterConfig:
            do_sample = False
            temperature = 0.000001
            pad_token_id = 151643
            eos_token_id = [151643, 151645]

        class ThinkerConfig:
            do_sample = False
            temperature = 1.0
            pad_token_id = None
            eos_token_id = None

        class Thinker:
            generation_config = ThinkerConfig()

        class Inner:
            generation_config = OuterConfig()
            thinker = Thinker()

        inner = Inner()
        _quiet_generation(inner)
        self.assertEqual(inner.generation_config.temperature, 1.0)
        self.assertEqual(inner.thinker.generation_config.pad_token_id, 151643)

    def test_missing_cache_is_offline(self) -> None:
        engine = QwenAsrEngine(load_model=MissingCacheLoader())
        with self.assertRaises(OfflineError):
            engine.transcribe(Path("a.wav"), "zh")

    def test_missing_qwen_asr_is_dependency(self) -> None:
        with patch.dict(sys.modules, {"qwen_asr": None}):
            with self.assertRaises(MissingDependencyError):
                load_qwen_from_cache("Qwen/Qwen3-ASR-0.6B")

    def test_load_skips_file_temperature(self) -> None:
        captured: dict = {}

        def from_pretrained(model_id, **kwargs):
            captured.update(kwargs)
            return object()

        qwen = type(sys)("qwen_asr")
        qwen.Qwen3ASRModel = type("M", (), {"from_pretrained": staticmethod(from_pretrained)})

        class GenerationConfig:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        transformers = type(sys)("transformers")
        transformers.GenerationConfig = GenerationConfig
        with patch.dict(sys.modules, {"qwen_asr": qwen, "transformers": transformers}):
            load_qwen_from_cache("local")
        config = captured["generation_config"]
        self.assertFalse(config.do_sample)
        self.assertEqual(config.temperature, 1.0)
        self.assertEqual(config.pad_token_id, 151643)


if __name__ == "__main__":
    unittest.main()
