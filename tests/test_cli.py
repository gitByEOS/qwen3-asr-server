"""无服务入口：参数校验、纯文本输出与脚本路径。"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import cli
from src.protocol.states import EnhanceState
from tests.fakes import FakeEngine, FakeEnhancer

ROOT = Path(__file__).resolve().parents[1]


class TestCommandLine(unittest.TestCase):
    def test_ac_asr_019(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "语音 样例.wav"
            source.touch()
            engine = FakeEngine()
            enhancer = FakeEnhancer()
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(cli, "QwenAsrEngine", return_value=engine), patch.object(
                cli, "FfmpegDspEnhancer", return_value=enhancer
            ), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = cli.main([str(source), "--enhance", "off", "--language", "Chinese"])
            self.assertEqual(code, 0)
            self.assertEqual(output.getvalue(), "你好\n")
            self.assertIn("开始转写", errors.getvalue())
            self.assertEqual(len(engine.calls), 1)
            self.assertEqual(engine.calls[0], (source, "Chinese"))
            self.assertEqual(enhancer.calls[0][1], EnhanceState.OFF)
            self.assertEqual(engine.release_count, 1)
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            self.assertEqual(os.environ["TRANSFORMERS_OFFLINE"], "1")

    def test_dependency_output_goes_to_stderr(self) -> None:
        class NoisyEngine(FakeEngine):
            def transcribe(self, *args, **kwargs):
                print("依赖内部日志")
                return super().transcribe(*args, **kwargs)

        with tempfile.NamedTemporaryFile(suffix=".wav") as source:
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(cli, "QwenAsrEngine", return_value=NoisyEngine()), patch.object(
                cli, "FfmpegDspEnhancer", return_value=FakeEnhancer()
            ), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = cli.main([source.name])
            self.assertEqual(code, 0)
            self.assertEqual(output.getvalue(), "你好\n")
            self.assertIn("依赖内部日志", errors.getvalue())

    def test_failure_is_nonzero_and_releases_model(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav") as source:
            engine = FakeEngine()
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(cli, "QwenAsrEngine", return_value=engine), patch.object(
                cli, "FfmpegDspEnhancer", return_value=FakeEnhancer()
            ), patch.object(engine, "transcribe", side_effect=RuntimeError("识别失败")), contextlib.redirect_stdout(
                output
            ), contextlib.redirect_stderr(errors):
                code = cli.main([source.name])
            self.assertEqual(code, 1)
            self.assertEqual(output.getvalue(), "")
            self.assertIn("识别失败", errors.getvalue())
            self.assertEqual(engine.release_count, 1)

    def test_invalid_input_does_not_create_engine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for arguments in ([str(Path(directory) / "missing.wav")], [directory], ["--enhance", "maybe"]):
                with self.subTest(arguments=arguments), patch.object(cli, "QwenAsrEngine") as factory:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                        cli.main(arguments)
                    self.assertEqual(caught.exception.code, 2)
                    factory.assert_not_called()

    def test_help_needs_no_model(self) -> None:
        output = io.StringIO()
        with patch.object(cli, "QwenAsrEngine") as factory, contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as caught:
                cli.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("--enhance", output.getvalue())
        factory.assert_not_called()

    def test_module_does_not_import_http_server(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-c", "import src.cli, sys; assert 'src.entry.server' not in sys.modules"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class TestTranscribeScript(unittest.TestCase):
    def test_shell_preserves_caller_paths_and_model_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "项目 空格"
            tools = root / "tools"
            tools.mkdir(parents=True)
            script = tools / "transcribe.sh"
            shutil.copyfile(ROOT / "tools/transcribe.sh", script)
            interpreter = root / ".venv/bin/python"
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "print(json.dumps({'args':sys.argv[1:], 'cwd':os.getcwd(), 'model':os.environ['QWEN_ASR_MODEL'], "
                "'offline':os.environ['HF_HUB_OFFLINE'], 'path':os.environ['PATH'], 'pythonpath':os.environ['PYTHONPATH']}))\n"
            )
            interpreter.chmod(0o755)
            caller = Path(directory) / "输入目录"
            caller.mkdir()
            env = dict(os.environ, QWEN_ASR_MODEL="/自定义/模型")
            result = subprocess.run(
                ["bash", str(script), "语音 样例.wav", "--enhance", "off"],
                cwd=caller, env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["args"], ["-B", "-m", "src.cli", "语音 样例.wav", "--enhance", "off"])
            self.assertEqual(Path(data["cwd"]).resolve(), caller.resolve())
            self.assertEqual(data["model"], "/自定义/模型")
            self.assertEqual(data["offline"], "1")
            self.assertEqual(Path(data["pythonpath"].split(os.pathsep)[0]).resolve(), root.resolve())
            self.assertEqual(Path(data["path"].split(os.pathsep)[0]).resolve(), (root / "bin").resolve())
            env.pop("QWEN_ASR_MODEL")
            result = subprocess.run(
                ["bash", str(script), "语音 样例.wav"],
                cwd=caller, env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                Path(json.loads(result.stdout)["model"]).resolve(), (root / "models/Qwen3-ASR-0.6B").resolve()
            )

    def test_real_shell_help_and_missing_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for arguments, expected in ((["--help"], 0), (["不存在.wav"], 2)):
                with self.subTest(arguments=arguments):
                    result = subprocess.run(
                        ["bash", str(ROOT / "tools/transcribe.sh"), *arguments],
                        cwd=directory, capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
