"""Apple Silicon MLX 引擎与自动后端选择。"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.asr.backend import resolve_backend
from src.asr.mlx_engine import MlxQwenAsrEngine, load_mlx_from_cache, mlx_language
from src.protocol.errors import OfflineError


class FakeMlxModel:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(self, audio: str, **kwargs):
        self.calls.append({"audio": audio, **kwargs})
        if kwargs.get("stream"):
            return iter(
                [
                    type("Event", (), {"text": "你", "language": "Chinese"})(),
                    type("Event", (), {"text": "好", "language": "Chinese"})(),
                ]
            )
        return type("Result", (), {"text": "你好", "language": "Chinese"})()


class RepeatingStream:
    def __init__(self) -> None:
        self.count = 0
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        self.count += 1
        if self.count > 100:
            raise AssertionError("重复生成未被终止")
        return type("Event", (), {"text": "魔", "language": "Chinese"})()

    def close(self) -> None:
        self.closed = True


class RepeatingMlxModel:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.streams: list[RepeatingStream] = []

    def generate(self, audio: str, **kwargs):
        self.calls.append({"audio": audio, **kwargs})
        stream = RepeatingStream()
        self.streams.append(stream)
        return stream


class TestMlxEngine(unittest.TestCase):
    def test_ac_asr_020(self) -> None:
        model = FakeMlxModel()
        loads: list[str] = []

        def load(model_id: str):
            loads.append(model_id)
            return model

        engine = MlxQwenAsrEngine(model_id="local", load_model=load)
        partials: list[str] = []
        statuses: list[str] = []
        text, language = engine.transcribe(
            Path("a.wav"), "zh", on_partial=partials.append, on_status=statuses.append
        )
        engine.transcribe(Path("b.wav"), "auto")
        self.assertEqual(text, "你好")
        self.assertEqual(language, "Chinese")
        self.assertEqual(partials, ["你", "你好"])
        self.assertEqual(loads, ["local"])
        self.assertEqual(engine.load_count, 1)
        self.assertIn("正在出字...", statuses)
        self.assertEqual(model.calls[0]["language"], "Chinese")

    def test_repeated_generation_is_stopped_and_stream_closed(self) -> None:
        model = RepeatingMlxModel()
        engine = MlxQwenAsrEngine(model_id="local", load_model=lambda _model_id: model)
        statuses: list[str] = []

        text, language = engine.transcribe(
            Path("loop.wav"), "auto", on_partial=lambda _text: None, on_status=statuses.append
        )

        self.assertLess(model.streams[0].count, 100)
        self.assertTrue(model.streams[0].closed)
        self.assertLessEqual(len(text), 8)
        self.assertEqual(language, "Chinese")
        self.assertIn("检测到重复输出，已提前结束", statuses)
        self.assertEqual(model.calls[0]["max_tokens"], 2048)

    def test_generation_context_is_cleared_after_each_audio(self) -> None:
        model = FakeMlxModel()
        engine = MlxQwenAsrEngine(model_id="local", load_model=lambda _model_id: model)

        with patch("src.asr.mlx_engine.clear_mlx_generation_context") as clear_context:
            engine.transcribe(Path("first.wav"), on_partial=lambda _text: None)
            engine.transcribe(Path("second.wav"), on_partial=lambda _text: None)

        self.assertEqual(clear_context.call_count, 2)

    def test_missing_local_model_is_offline(self) -> None:
        with self.assertRaises(OfflineError):
            load_mlx_from_cache("not-a-local-model")

    def test_language_alias(self) -> None:
        self.assertIsNone(mlx_language("auto"))
        self.assertEqual(mlx_language("zh"), "Chinese")
        self.assertEqual(mlx_language("English"), "English")


class TestBackend(unittest.TestCase):
    def test_auto_uses_mlx_on_apple_silicon(self) -> None:
        with patch("src.asr.backend.platform.system", return_value="Darwin"), patch(
            "src.asr.backend.platform.machine", return_value="arm64"
        ), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_backend(), "mlx")

    def test_auto_uses_torch_elsewhere(self) -> None:
        with patch("src.asr.backend.platform.system", return_value="Linux"), patch(
            "src.asr.backend.platform.machine", return_value="x86_64"
        ), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_backend(), "torch")

    def test_explicit_backend_wins(self) -> None:
        with patch.dict(os.environ, {"QWEN_ASR_BACKEND": "torch"}):
            self.assertEqual(resolve_backend(), "torch")

    def test_invalid_backend_fails_early(self) -> None:
        with self.assertRaises(ValueError):
            resolve_backend("cuda")


if __name__ == "__main__":
    unittest.main()
