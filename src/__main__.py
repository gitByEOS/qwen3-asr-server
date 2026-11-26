"""进程入口：装配各层后启动。"""

from src.asr.qwen_engine import DEFAULT_MODEL_ID, QwenAsrEngine
from src.audio.ffmpeg_dsp import FfmpegDspEnhancer
from src.entry.server import App, serve
from src.pipeline.runner import Pipeline
from src.runtime.offline import enable_offline_mode


def main() -> None:
    enable_offline_mode()
    engine = QwenAsrEngine()
    app = App(
        pipeline=Pipeline(FfmpegDspEnhancer(), engine),
        model_id=engine.model_id or DEFAULT_MODEL_ID,
        enhancer_name="ffmpeg-dsp",
    )
    serve(app)


if __name__ == "__main__":
    main()
