"""AC-WEB：转写页与 enhance 开关。"""

from __future__ import annotations

import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from src.entry.page import HTML
from src.entry.server import App, make_handler
from src.pipeline.runner import Pipeline
from tests.fakes import FakeEngine, FakeEnhancer


class TestWebPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app = App(
            pipeline=Pipeline(FakeEnhancer(), FakeEngine()),
            model_id="Qwen/Qwen3-ASR-0.6B",
            enhancer_name="ffmpeg-dsp",
        )
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def _html(self) -> str:
        with urlopen(self.base + "/", timeout=2) as response:
            self.assertEqual(response.status, 200)
            return response.read().decode()

    def test_ac_web_001(self) -> None:
        html = self._html()
        self.assertIn('type="file"', html)
        self.assertIn('id="enhance"', html)
        self.assertIn('id="submit"', html)

    def test_ac_web_002(self) -> None:
        self.assertIn("result.textContent = data.text", HTML)

    def test_ac_web_003(self) -> None:
        submit = HTML.split('form.addEventListener("submit"')[1]
        before_fetch = submit.split("fetch(")[0]
        self.assertIn("if (busy) return", before_fetch)

    def test_ac_web_004(self) -> None:
        self.assertIn("data.error", HTML)
        self.assertIn("if (!response.ok)", HTML)

    def test_ac_web_006(self) -> None:
        self.assertIn('enhanceBox.checked ? "on" : "off"', HTML)
        self.assertIn("enhanceState.textContent = data.enhance", HTML)
        self.assertIn('type="checkbox" checked', HTML)

    def test_ac_web_007(self) -> None:
        html = self._html()
        self.assertIn('id="drop-zone"', html)
        self.assertIn("drag-over", HTML)
        self.assertIn("dataTransfer.files", HTML)

    def test_ac_web_008(self) -> None:
        self.assertIn("data.missing", HTML)
        self.assertIn("warning", HTML)

    def test_ac_web_009(self) -> None:
        html = self._html()
        self.assertIn('id="log"', html)
        self.assertIn("EventSource", HTML)
        self.assertIn("/api/events", HTML)

    def test_ac_web_011(self) -> None:
        self.assertIn("data.busy", HTML)
        self.assertIn("setBusy(true)", HTML)
        self.assertIn("submit.disabled = on", HTML)

    def test_ac_web_012(self) -> None:
        submit = HTML.split('form.addEventListener("submit"')[1]
        before_fetch = submit.split("fetch(")[0]
        self.assertIn("请先拖入文件", before_fetch)
        self.assertIn("if (!file)", before_fetch)

    def test_ac_web_013(self) -> None:
        events = HTML.split("events.onmessage")[1].split('form.addEventListener("submit"')[0]
        self.assertIn("data.text", events)
        self.assertIn("result.textContent = data.text", events)
        self.assertNotIn("result.textContent = data.log", events)
        submit = HTML.split('form.addEventListener("submit"')[1]
        self.assertIn('result.textContent = "等待出字..."', submit)

    def test_submit_clears_previous_logs(self) -> None:
        submit = HTML.split('form.addEventListener("submit"')[1]
        before_fetch = submit.split("fetch(")[0]
        self.assertIn('log.textContent = ""', before_fetch)
        self.assertLess(
            before_fetch.index('log.textContent = ""'),
            before_fetch.index('appendLog("提交 " + file.name)'),
        )

    def test_to_agent_shows_current_curl_endpoint(self) -> None:
        self.assertIn("[to-agent]", HTML)
        self.assertIn('id="agent-curl"', HTML)
        self.assertIn('file=@/path/to/audio.mp4', HTML)
        self.assertIn('language=auto', HTML)
        self.assertIn('enhance=on', HTML)
        self.assertIn('window.location.origin}${transcribePath}', HTML)
        self.assertIn('!agentHelp.contains(event.target)', HTML)
        self.assertIn('agentHelp.open = false', HTML)
