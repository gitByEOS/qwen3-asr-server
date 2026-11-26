"""AC-ASR：health 与 transcribe HTTP。"""

from __future__ import annotations

import json
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.audio.ffmpeg_dsp import ffmpeg_args
from src.entry.server import App, _run_until_stop, make_handler, serve
from src.pipeline.runner import Pipeline
from src.protocol.errors import MissingDependencyError
from src.protocol.states import EnhanceState
from src.runtime.offline import enable_offline_mode
from tests.fakes import FakeEngine, FakeEnhancer, MissingCacheLoader
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

    def prepare(self, audio_path: Path, enhance: EnhanceState) -> list[Path]:
        self.last_enhance = enhance
        self.last_args = ffmpeg_args(audio_path, Path("out.wav"), enhance)
        return [audio_path]


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
        self.app = app
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

    def test_ac_asr_010(self) -> None:
        class MissingFfmpeg:
            def prepare(self, audio_path, enhance):
                raise MissingDependencyError("需要 ffmpeg")

        app = App(
            pipeline=Pipeline(MissingFfmpeg(), FakeEngine()),
            model_id="Qwen/Qwen3-ASR-0.6B",
            enhancer_name="ffmpeg-dsp",
        )
        self.server.shutdown()
        self.server.server_close()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        body, content_type = _multipart({}, {"file": ("a.mp3", b"xxx")})
        status, payload = self._json("POST", "/api/transcribe", body, {"Content-Type": content_type})
        self.assertEqual(status, 503)
        self.assertIn("ffmpeg", payload["error"])
        status, health = self._json("GET", "/health")
        self.assertEqual(status, 200)

    def test_ac_asr_011(self) -> None:
        status, payload = self._json("GET", "/health")
        self.assertEqual(status, 200)
        self.assertIn("ffmpeg", payload["capabilities"])
        self.assertIn("qwen_asr", payload["capabilities"])
        self.assertIn("torch", payload["capabilities"])
        self.assertIn("missing", payload)

    def test_ac_asr_012(self) -> None:
        from unittest.mock import patch

        from src.audio.ffmpeg_dsp import FfmpegDspEnhancer

        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=False):
            app = App(
                pipeline=Pipeline(FfmpegDspEnhancer(), FakeEngine()),
                model_id="Qwen/Qwen3-ASR-0.6B",
                enhancer_name="ffmpeg-dsp",
            )
            self.server.shutdown()
            self.server.server_close()
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
            self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            body, content_type = _multipart({"enhance": "off"}, {"file": ("a.wav", b"RIFF")})
            status, payload = self._json("POST", "/api/transcribe", body, {"Content-Type": content_type})
        self.assertEqual(status, 200)
        self.assertTrue(payload["text"])
        self.assertEqual(payload["enhance"], "off")

    def test_ac_web_010(self) -> None:
        chunks: list[str] = []
        ready = threading.Event()
        got = threading.Event()

        def listen() -> None:
            try:
                with urlopen(self.base + "/api/events", timeout=5) as response:
                    ready.set()
                    while not got.is_set():
                        line = response.fp.readline()
                        if not line:
                            break
                        chunks.append(line.decode())
                        text = "".join(chunks)
                        if "开始处理第" in text and "你好" in text:
                            got.set()
                            break
            except Exception:
                ready.set()

        worker = threading.Thread(target=listen, daemon=True)
        worker.start()
        self.assertTrue(ready.wait(timeout=2))
        body, content_type = _multipart({}, {"file": ("a.wav", b"RIFF")})
        status, payload = self._json("POST", "/api/transcribe", body, {"Content-Type": content_type})
        self.assertEqual(status, 200)
        self.assertTrue(got.wait(timeout=2), "".join(chunks))
        worker.join(timeout=1)

    def test_ac_asr_015(self) -> None:
        from tests.test_pipeline import BlockingEnhancer

        blocker = BlockingEnhancer()
        app = App(
            pipeline=Pipeline(blocker, FakeEngine()),
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
        status, payload = self._json("GET", "/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["busy"])
        blocker.release.set()
        worker.join(timeout=2)
        status, payload = self._json("GET", "/health")
        self.assertFalse(payload["busy"])

    def test_ac_asr_016(self) -> None:
        self.app.logs.emit({"log": "冷启动加载模型", "busy": True})
        with urlopen(self.base + "/api/events", timeout=3) as response:
            text = ""
            while "冷启动加载模型" not in text:
                line = response.fp.readline()
                if not line:
                    break
                text += line.decode()
        self.assertIn("冷启动加载模型", text)


class TestOccupiedPort(unittest.TestCase):
    def test_occupied_port_exits(self) -> None:
        held = socket.socket()
        held.bind(("127.0.0.1", 0))
        held.listen(1)
        port = held.getsockname()[1]
        app = App(
            pipeline=Pipeline(FakeEnhancer(), FakeEngine()),
            model_id="Qwen/Qwen3-ASR-0.6B",
            enhancer_name="ffmpeg-dsp",
        )
        with self.assertRaises(SystemExit) as caught:
            serve(app, host="127.0.0.1", port=port)
        held.close()
        self.assertEqual(caught.exception.code, 1)

    def test_ctrl_c_closes(self) -> None:
        class Stopped:
            def __init__(self) -> None:
                self.closed = False

            def serve_forever(self) -> None:
                raise KeyboardInterrupt

            def server_close(self) -> None:
                self.closed = True

        server = Stopped()
        _run_until_stop(server)
        self.assertTrue(server.closed)
