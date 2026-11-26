"""单文件离线转写入口，不启动 HTTP 服务。"""

from __future__ import annotations

import argparse
import sys
from contextlib import redirect_stdout
from pathlib import Path

from src.asr.backend import create_engine
from src.audio.ffmpeg_dsp import FfmpegDspEnhancer
from src.pipeline.runner import Pipeline
from src.runtime.offline import enable_offline_mode

PROGRESS_MESSAGES = {"开始转写", "人声增强", "音频直通", "转码中", "整段解析", "加载模型...", "模型已加载"}


def print_progress(message: str) -> None:
    if message in PROGRESS_MESSAGES or message.startswith(("切成 ", "开始处理第 ", "第 ")):
        print(message, file=sys.stderr, flush=True)


def arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="离线转写一个音视频文件，结果输出到标准输出", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    parser.add_argument("file", type=Path, help="音视频文件路径")
    parser.add_argument("--enhance", choices=("on", "off"), default="on", help="人声增强，默认 on")
    parser.add_argument("--language", default="auto", help="识别语言，默认自动检测")
    options = parser.parse_args(argv)
    if not options.file.is_file():
        parser.error(f"文件不存在或不是普通文件：{options.file}")
    return options


def main(argv: list[str] | None = None) -> int:
    options = arguments(argv)
    enable_offline_mode()
    _backend, engine = create_engine()
    try:
        with redirect_stdout(sys.stderr):
            result = Pipeline(FfmpegDspEnhancer(), engine).run(
                options.file,
                language=options.language,
                enhance=options.enhance,
                on_progress=print_progress,
            )
        print(result.text)
        return 0
    except Exception as error:
        print(f"转写失败：{error}", file=sys.stderr)
        return 1
    finally:
        engine.release()


if __name__ == "__main__":
    raise SystemExit(main())
