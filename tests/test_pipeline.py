"""L2 编排：单飞、一次 ASR、enhance 原样下传。"""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from src.pipeline.runner import Pipeline, piece_seconds
from src.protocol.errors import BusyError
from src.protocol.states import EnhanceState
from tests.fakes import FakeEngine, FakeEnhancer


class BlockingEnhancer:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def prepare(self, audio_path: Path, enhance: EnhanceState) -> list[Path]:
        self.started.set()
        self.release.wait(timeout=2)
        return [audio_path]


class TestPipeline(unittest.TestCase):
    def test_single_engine_call(self) -> None:
        enhancer = FakeEnhancer()
        engine = FakeEngine()
        pipeline = Pipeline(enhancer, engine)
        result = pipeline.run(Path("a.wav"), language="zh", enhance="off")
        self.assertEqual(result.text, "你好")
        self.assertEqual(result.enhance, EnhanceState.OFF)
        self.assertEqual(len(engine.calls), 1)
        self.assertEqual(enhancer.calls[0][1], EnhanceState.OFF)

    def test_default_enhance_on(self) -> None:
        enhancer = FakeEnhancer()
        pipeline = Pipeline(enhancer, FakeEngine())
        result = pipeline.run(Path("a.wav"))
        self.assertEqual(result.enhance, EnhanceState.ON)

    def test_busy_rejects_second_run(self) -> None:
        blocker = BlockingEnhancer()
        pipeline = Pipeline(blocker, FakeEngine())
        worker = threading.Thread(target=pipeline.run, args=(Path("a.wav"),))
        worker.start()
        self.assertTrue(blocker.started.wait(timeout=1))
        with self.assertRaises(BusyError):
            pipeline.run(Path("b.wav"))
        blocker.release.set()
        worker.join(timeout=2)

    def test_ac_asr_013(self) -> None:
        engine = FakeEngine()
        pipeline = Pipeline(FakeEnhancer(), engine)
        pipeline.run(Path("a.wav"))
        self.assertIsNotNone(engine.model)
        for _ in range(4):
            self.assertFalse(pipeline.heartbeat())
        self.assertIsNotNone(engine.model)
        self.assertTrue(pipeline.heartbeat())
        self.assertIsNone(engine.model)
        self.assertEqual(engine.release_count, 1)
        pipeline.run(Path("b.wav"))
        self.assertIsNotNone(engine.model)
        self.assertEqual(len(engine.calls), 2)

    def test_ac_asr_014(self) -> None:
        notes: list[str] = []
        pipeline = Pipeline(FakeEnhancer(), FakeEngine())
        result = pipeline.run(Path("a.wav"), on_progress=notes.append)
        self.assertIn("开始转写", notes)
        self.assertIn("转码中", notes)
        self.assertIn("开始处理第 1/1 段，时长 0 s", notes)
        self.assertEqual(notes[-1], result.text)

    def test_render_removed_source_kept(self) -> None:
        source_fd, source_name = tempfile.mkstemp(suffix=".wav")
        render_fd, render_name = tempfile.mkstemp(suffix=".wav")
        os.close(source_fd)
        os.close(render_fd)
        source = Path(source_name)
        render = Path(render_name)

        class Split:
            def prepare(self, audio_path: Path, enhance: EnhanceState) -> list[Path]:
                return [audio_path, render]

        try:
            Pipeline(Split(), FakeEngine()).run(source)
            self.assertTrue(source.exists())
            self.assertFalse(render.exists())
        finally:
            source.unlink(missing_ok=True)
            render.unlink(missing_ok=True)

    def test_cleanup_failure_releases_lock(self) -> None:
        engine = FakeEngine()
        pipeline = Pipeline(FakeEnhancer(), engine)
        with patch("src.pipeline.runner._drop_renders", side_effect=PermissionError("切片无法删除")):
            with self.assertRaisesRegex(PermissionError, "切片无法删除"):
                pipeline.run(Path("a.wav"))
        self.assertFalse(pipeline.is_busy())
        for _ in range(5):
            pipeline.heartbeat()
        self.assertEqual(engine.release_count, 1)
        self.assertEqual(pipeline.run(Path("b.wav")).text, "你好")

    def test_engine_failure_releases_lock(self) -> None:
        engine = FakeEngine()
        pipeline = Pipeline(FakeEnhancer(), engine)
        with patch.object(engine, "transcribe", side_effect=RuntimeError("识别失败")):
            with self.assertRaisesRegex(RuntimeError, "识别失败"):
                pipeline.run(Path("a.wav"))
        self.assertFalse(pipeline.is_busy())
        self.assertEqual(pipeline.run(Path("b.wav")).text, "你好")

    def test_piece_seconds_reads_wav(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
            with wave.open(handle.name, "wb") as target:
                target.setnchannels(1)
                target.setsampwidth(2)
                target.setframerate(16000)
                target.writeframes(b"\x00\x00" * 16000)
            self.assertEqual(piece_seconds(Path(handle.name)), "1")


if __name__ == "__main__":
    unittest.main()
