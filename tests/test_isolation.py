"""L1 不得引用 L3/L5。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestLayerIsolation(unittest.TestCase):
    def test_entry_does_not_import_asr_or_audio(self) -> None:
        for path in (ROOT / "src/entry").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("src.asr", text, path.name)
            self.assertNotIn("src.audio", text, path.name)

    def test_asr_does_not_import_audio(self) -> None:
        for path in (ROOT / "src/asr").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("src.audio", text, path.name)
            self.assertNotIn("src.entry", text, path.name)
