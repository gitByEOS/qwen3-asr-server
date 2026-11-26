"""AC-ASR：health 与 transcribe HTTP。"""

from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.audio.ffmpeg_dsp import ffmpeg_args
from src.entry.server import App, make_handler
from src.pipeline.runner import Pipeline
from src.protocol.states import EnhanceState
from src.runtime.offline import enable_offline_mode
from tests.fakes import FakeEngine, MissingCacheLoader
from src.asr.qwen_engine import QwenAsrEngine


def _multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----testboundary"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(value.encode() + b"\r\n")
    for name, (filename, data) in files.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        chunks.append(b"Content-Type: audio/wav\r\n\r\n")
        chunks.append(data + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class RecordingEnhancer:
    def __init__(self) -> None:
        self.last_enhance: EnhanceState | None = None
        self.last_args: list[str] = []

    def prepare(self, audio_path: Path, enhance: EnhanceState) -> Path:
        self.last_enhance = enhance
        self.last_args = ffmpeg_args(audio_path, Path("out.wav"), enhance)
        return audio_path


class HttpCase(unittest.TestCase):
    def setUp(self) -> None:
        enable_offline_mode()
        self.enhancer = RecordingEnhancer()
        self.engine = FakeEngine()
        self.engine.load_count = 0
        pipeline = Pipeline(self.enhancer, self.engine)
        app = App(
            pipeline=pipeline,
            model_id="Qwen/Qwen3-ASR-0.6B",
            enhancer_name="ffmpeg-dsp",
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _json(self, method: str, path: str, body: bytes | None = None, headers: dict | None = None):
        request = Request(self.base + path, data=body, method=method, headers=headers or {})
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read().decode())
        except HTTPError as error:
            return error.code, json.loads(error.read().decode())

    def test_ac_asr_001(self) -> None:
        status, payload = self._json("GET", "/health")
        self.assertEqual(status, 200)
        self.assertIn("ok", payload)
        self.assertEqual(payload["model"], "Qwen/Qwen3-ASR-0.6B")
        self.assertEqual(payload["enhancer"], "ffmpeg-dsp")
        self.assertIn("offline", payload)
        self.assertEqual(self.engine.load_count, 0)

    def test_ac_asr_002(self) -> None:
        body, content_type = _multipart({}, {"file": ("a.wav", b"RIFF....")})
        status, payload = self._json("POST", "/api/transcribe", body, {"Content-Type": content_type})
        self.assertEqual(status, 200)
        self.assertTrue(payload["text"])
        self.assertIn("enhance", payload)
        self.assertNotIn("segments", payload)
        self.assertNotIn("srt", payload)

    def test_ac_asr_003(self) -> None:
        empty, content_type = _multipart({}, {"file": ("a.wav", b"")})
        status, payload = self._json("POST", "/api/transcribe", empty, {"Content-Type": content_type})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        self.assertEqual(len(self.engine.calls), 0)

        huge_headers = {
            "Content-Type": "multipart/form-data; boundary=x",
            "Content-Length": str(50 * 1024 * 1024 + 1),
        }
        status, payload = self._json("POST", "/api/transcribe", b"", huge_headers)
        self.assertEqual(status, 413)
        self.assertIn("error", payload)

        status, payload = self._json(
            "POST", "/api/transcribe", b"{}", {"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)

        bad, content_type = _multipart({"enhance": "maybe"}, {"file": ("a.wav", b"RIFF")})
        status, payload = self._json("POST", "/api/transcribe", bad, {"Content-Type": content_type})
        self.assertEqual(status, 400)
        self.assertEqual(len(self.engine.calls), 0)

    def test_ac_asr_004(self) -> None:
        engine = QwenAsrEngine(load_model=MissingCacheLoader())
        engine.load_count = 0
        app = App(
            pipeline=Pipeline(self.enhancer, engine),
            model_id=engine.model_id,
            enhancer_name="ffmpeg-dsp",
        )
        self.server.shutdown()
        self.server.server_close()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        loader = engine._load_model
        body, content_type = _multipart({}, {"file": ("a.wav", b"RIFF")})
        status, payload = self._json("POST", "/api/transcribe", body, {"Content-Type": content_type})
        self.assertEqual(status, 503)
        self.assertIn("离线", payload["error"])
        self.assertEqual(loader.network, 0)

    def test_ac_asr_005(self) -> None:
        from tests.test_pipeline import BlockingEnhancer

        blocker = BlockingEnhancer()
        engine = FakeEngine()
        app = App(
            pipeline=Pipeline(blocker, engine),
            model_id="Qwen/Qwen3-ASR-0.6B",
            enhancer_name="ffmpeg-dsp",
        )
        self.server.shutdown()
        self.server.server_close()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        body, content_type = _multipart({}, {"file": ("a.wav", b"RIFF")})
        headers = {"Content-Type": content_type}

        def first() -> None:
            try:
                urlopen(Request(self.base + "/api/transcribe", data=body, method="POST", headers=headers), timeout=3)
            except Exception:
                pass

        worker = threading.Thread(target=first)
        worker.start()
        self.assertTrue(blocker.started.wait(timeout=2))
        status, payload = self._json("POST", "/api/transcribe", body, headers)
        self.assertEqual(status, 429)
        self.assertIn("error", payload)
        blocker.release.set()
        worker.join(timeout=2)

    def test_ac_asr_008(self) -> None:
        body, content_type = _multipart({}, {"file": ("a.wav", b"RIFF")})
        status, payload = self._json("POST", "/api/transcribe", body, {"Content-Type": content_type})
        self.assertEqual(status, 200)
        self.assertEqual(payload["enhance"], "on")
        self.assertIn("-af", self.enhancer.last_args)
        self.assertIn("highpass=f=80", ",".join(self.enhancer.last_args))

    def test_ac_asr_009(self) -> None:
        body, content_type = _multipart({"enhance": "off"}, {"file": ("a.wav", b"RIFF")})
        status, payload = self._json("POST", "/api/transcribe", body, {"Content-Type": content_type})
        self.assertEqual(status, 200)
        self.assertEqual(payload["enhance"], "off")
        self.assertNotIn("-af", self.enhancer.last_args)
        self.assertEqual(len(self.engine.calls), 1)
