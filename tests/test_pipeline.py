"""L2 编排：单飞、一次 ASR、enhance 原样下传。"""

from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path

from src.pipeline.runner import Pipeline
from src.protocol.errors import BusyError
from src.protocol.states import EnhanceState
from tests.fakes import FakeEngine, FakeEnhancer


class BlockingEnhancer:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def prepare(self, audio_path: Path, enhance: EnhanceState) -> Path:
        self.started.set()
        self.release.wait(timeout=2)
        return audio_path


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


if __name__ == "__main__":
    unittest.main()
