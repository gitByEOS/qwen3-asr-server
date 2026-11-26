"""L1 HTTP：health 与 transcribe。不加载模型。"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Empty
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

from src.entry.logs import LogBus
from src.entry.multipart import parse_multipart
from src.entry.page import HTML
from src.pipeline.runner import Pipeline
from src.protocol.errors import BusyError, MissingDependencyError, OfflineError
from src.protocol.states import EnhanceState
from src.runtime.capabilities import missing_of, probe
from src.runtime.offline import is_offline

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DEFAULT_PORT = 11801
HEARTBEAT_SECONDS = 30


@dataclass
class App:
    pipeline: Pipeline
    model_id: str
    enhancer_name: str
    logs: LogBus = field(default_factory=LogBus)


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def handle(self) -> None:
            try:
                super().handle()
            except (ConnectionResetError, BrokenPipeError):
                return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                capabilities = probe()
                self._json(200, {
                    "ok": True,
                    "model": app.model_id,
                    "enhancer": app.enhancer_name,
                    "offline": is_offline(),
                    "capabilities": capabilities,
                    "missing": missing_of(capabilities),
                    "busy": app.pipeline.is_busy(),
                })
                return
            if path in ("/", ""):
                model_name = Path(app.model_id).name or app.model_id
                payload = HTML.replace("{{model}}", model_name).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if path == "/api/events":
                self._events()
                return
            self._json(404, {"error": "未找到"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/transcribe":
                self._json(404, {"error": "未找到"})
                return
            self._transcribe()

        def _transcribe(self) -> None:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._json(400, {"error": "需要 multipart 音视频"})
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self._json(400, {"error": "无效长度"})
                return
            if length > MAX_UPLOAD_BYTES:
                self._json(413, {"error": "文件超过 50MB"})
                return
            body = self.rfile.read(length)
            fields = parse_multipart(content_type, body)
            if "file" not in fields:
                self._json(400, {"error": "缺少文件"})
                return
            filename, payload = fields["file"]
            if not payload:
                self._json(400, {"error": "空文件"})
                return
            enhance_raw = _field_text(fields.get("enhance"))
            try:
                enhance = EnhanceState.parse(enhance_raw)
            except ValueError as error:
                self._json(400, {"error": str(error)})
                return
            language = _field_text(fields.get("language")) or "auto"
            suffix = Path(filename or "audio.wav").suffix or ".wav"
            with NamedTemporaryFile(suffix=suffix, delete=False) as handle:
                handle.write(payload)
                upload_path = Path(handle.name)
            try:
                result = app.pipeline.run(
                    upload_path,
                    language=language,
                    enhance=enhance,
                    on_progress=lambda message: app.logs.emit({"log": message, "busy": True}),
                    on_partial=lambda text: app.logs.emit({"text": text, "busy": True}),
                )
            except BusyError as error:
                self._json(429, {"error": str(error)})
                return
            except (OfflineError, MissingDependencyError) as error:
                app.logs.emit({"busy": False})
                self._json(503, {"error": str(error)})
                return
            except Exception as error:
                print(f"转写失败：{error}", flush=True)
                app.logs.emit({"busy": False})
                self._json(500, {"error": str(error)})
                return
            app.logs.emit({"busy": False})
            self._json(200, {
                "text": result.text,
                "language": result.language,
                "enhance": result.enhance.value,
            })

        def _events(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            queue, history = app.logs.subscribe()
            try:
                for payload in history:
                    self._write_event(payload)
                while True:
                    try:
                        payload = queue.get(timeout=15)
                    except Empty:
                        self.wfile.write(b": \n\n")
                        self.wfile.flush()
                        continue
                    self._write_event(payload)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                return
            finally:
                app.logs.unsubscribe(queue)

        def _write_event(self, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False)
            self.wfile.write(f"data: {body}\n\n".encode("utf-8"))
            self.wfile.flush()

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(app: App, host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(app))
    threading.Thread(target=_idle_watch, args=(app,), daemon=True).start()
    server.serve_forever()


def _idle_watch(app: App, seconds: int = HEARTBEAT_SECONDS) -> None:
    while True:
        time.sleep(seconds)
        if app.pipeline.heartbeat():
            app.logs.emit({"log": "模型已卸载，下次转写会冷启动"})


def _field_text(item: tuple[str | None, bytes] | None) -> str | None:
    if item is None:
        return None
    return item[1].decode("utf-8").strip()
