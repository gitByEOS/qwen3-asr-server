"""安装脚本：解释器版本、环境保护与无下载校验。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAKE_COMMAND = r'''
import json
import os
import shutil
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
root = Path(os.environ["SETUP_TEST_ROOT"])
with (root / "calls.jsonl").open("a") as log:
    log.write(json.dumps([name, *args]) + "\n")
if name == "uv":
    if args == ["python", "install", "3.12"] and os.environ.get("SETUP_TEST_INSTALL_FAILURE"):
        print("解释器下载失败", file=sys.stderr)
        raise SystemExit(1)
    if args[:2] == ["python", "find"]:
        print(root / "bin/python3.12")
    elif args[:1] == ["venv"]:
        destination = Path(args[1]) / "bin/python"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / "bin/python3.12", destination)
        destination.chmod(0o755)
    raise SystemExit(0)
if name in ("python", "python3.12"):
    if args[:1] == ["-c"]:
        if os.environ.get("SETUP_TEST_BROKEN_PYTHON"):
            raise SystemExit(1)
        print(os.environ.get("SETUP_TEST_VERSION", "3.12"))
    elif args == ["-"]:
        sys.stdin.read()
        print("完备")
    raise SystemExit(0)
raise SystemExit("不允许测试下载或调用外部服务")
'''


class TestSetup(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "项目 空格"
        (self.root / "tools").mkdir(parents=True)
        (self.root / "bin").mkdir()
        shutil.copyfile(ROOT / "tools/setup.sh", self.root / "tools/setup.sh")
        model = self.root / "models/Qwen3-ASR-0.6B"
        model.mkdir(parents=True)
        (model / "config.json").write_text("{}")
        for name in ("uv", "python3.12", "ffmpeg", "curl"):
            command = self.root / "bin" / name
            command.write_text(f"#!{sys.executable}\n" + FAKE_COMMAND)
            command.chmod(0o755)
        self.env = dict(os.environ, SETUP_TEST_ROOT=str(self.root))
        hooks = self.root / "shell_hooks"
        hooks.write_text(
            'command() {\n'
            '  if [[ "$1" == "-v" && ",${SETUP_TEST_MISSING:-}," == *",$2,"* ]]; then\n'
            '    return 1\n'
            '  fi\n'
            '  builtin command "$@"\n'
            '}\n'
        )
        self.env["BASH_ENV"] = str(hooks)

    def environment(self, version: str = "3.12", is_broken: bool = False) -> Path:
        python = self.root / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        shutil.copyfile(self.root / "bin/python3.12", python)
        python.chmod(0o755)
        self.env["SETUP_TEST_VERSION"] = version
        if is_broken:
            self.env["SETUP_TEST_BROKEN_PYTHON"] = "1"
        return python

    def run_setup(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", str(self.root / "tools/setup.sh"), *arguments],
            env=self.env, capture_output=True, text=True, timeout=10,
        )

    def calls(self) -> list[list[str]]:
        log = self.root / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_new_environment_uses_local_python_312(self) -> None:
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        venv = [call for call in self.calls() if call[:2] == ["uv", "venv"]]
        self.assertEqual(len(venv), 1)
        self.assertEqual(Path(venv[0][-1]).resolve(), (self.root / "bin/python3.12").resolve())
        self.assertNotIn(["uv", "python", "install", "3.12"], self.calls())
        self.assertTrue(any(call[:2] == ["python", "-c"] for call in self.calls()))

    def test_missing_python_312_is_prepared_by_uv(self) -> None:
        self.env["SETUP_TEST_MISSING"] = "python3.12"
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(["uv", "python", "install", "3.12"], self.calls())
        self.assertIn(["uv", "python", "find", "3.12"], self.calls())
        self.assertTrue((self.root / ".venv/bin/python").exists())

    def test_python_install_failure_stops_before_environment_creation(self) -> None:
        self.env["SETUP_TEST_MISSING"] = "python3.12"
        self.env["SETUP_TEST_INSTALL_FAILURE"] = "1"
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("解释器下载失败", result.stderr)
        self.assertFalse((self.root / ".venv").exists())
        self.assertEqual(self.calls(), [["uv", "python", "install", "3.12"]])

    def test_existing_python_312_is_reused(self) -> None:
        python = self.environment()
        original = python.read_bytes()
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(python.read_bytes(), original)
        self.assertFalse(any(call[:2] == ["uv", "venv"] for call in self.calls()))
        self.assertTrue(any(call[:3] == ["uv", "pip", "install"] for call in self.calls()))

    def test_existing_python_313_is_rejected_before_download(self) -> None:
        python = self.environment("3.13")
        original = python.read_bytes()
        self.env["SETUP_TEST_MISSING"] = "ffmpeg"
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("3.12", result.stderr)
        self.assertIn("3.13", result.stderr)
        self.assertIn("保留", result.stderr)
        self.assertEqual(python.read_bytes(), original)
        self.assertFalse(any(call[0] in ("uv", "curl") for call in self.calls()))

    def test_incomplete_environment_is_preserved(self) -> None:
        marker = self.root / ".venv/用户文件"
        marker.parent.mkdir()
        marker.write_text("不能删除")
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".venv", result.stderr)
        self.assertIn("保留", result.stderr)
        self.assertEqual(marker.read_text(), "不能删除")
        self.assertFalse(any(call[0] == "uv" for call in self.calls()))

    def test_broken_interpreter_is_rejected(self) -> None:
        python = self.environment(is_broken=True)
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("解释器", result.stderr)
        self.assertIn("保留", result.stderr)
        self.assertTrue(python.exists())
        self.assertFalse(any(call[0] == "uv" for call in self.calls()))

    def test_missing_uv_fails_before_creating_environment(self) -> None:
        self.env["SETUP_TEST_MISSING"] = "uv"
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uv", result.stderr)
        self.assertFalse((self.root / ".venv").exists())
        self.assertEqual(self.calls(), [])

    def test_check_accepts_312_without_installing(self) -> None:
        self.environment()
        self.env["SETUP_TEST_MISSING"] = "uv"
        result = self.run_setup("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("完备", result.stdout)
        self.assertTrue(any(call[:2] == ["python", "-c"] for call in self.calls()))
        self.assertFalse(any(call[0] == "uv" for call in self.calls()))

    def test_check_rejects_incompatible_environment(self) -> None:
        self.environment("3.13")
        result = self.run_setup("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("3.12", result.stderr)
        self.assertIn("3.13", result.stderr)
        self.assertNotIn(["python", "-"], self.calls())

    def test_check_reports_missing_environment(self) -> None:
        result = self.run_setup("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("先运行", result.stderr)
        self.assertIn("setup.sh", result.stderr)
        self.assertFalse((self.root / ".venv").exists())
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
