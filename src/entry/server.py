"""L1 HTTP：health 与 transcribe。不加载模型。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

from src.entry.multipart import parse_multipart
from src.pipeline.runner import Pipeline
from src.protocol.errors import BusyError, OfflineError
from src.protocol.states import EnhanceState
from src.runtime.ffmpeg import is_ffmpeg_ready
from src.runtime.offline import is_offline

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DEFAULT_PORT = 11801


@dataclass
class App:
    pipeline: Pipeline
    model_id: str
    enhancer_name: str


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._json(200, {
                    "ok": is_ffmpeg_ready(),
                    "model": app.model_id,
                    "enhancer": app.enhancer_name,
                    "offline": is_offline(),
                })
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
                result = app.pipeline.run(upload_path, language=language, enhance=enhance)
            except BusyError as error:
                self._json(429, {"error": str(error)})
                return
            except OfflineError as error:
                self._json(503, {"error": str(error)})
                return
            self._json(200, {
                "text": result.text,
                "language": result.language,
                "enhance": result.enhance.value,
            })

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
    server.serve_forever()


def _field_text(item: tuple[str | None, bytes] | None) -> str | None:
    if item is None:
        return None
    return item[1].decode("utf-8").strip()
