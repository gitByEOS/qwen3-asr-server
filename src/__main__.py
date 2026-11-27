"""进程入口：装配各层后启动。"""

import os

from src.asr.backend import create_engine
from src.audio.ffmpeg_dsp import FfmpegDspEnhancer
from src.entry.server import DEFAULT_PORT, App, serve
from src.pipeline.runner import Pipeline
from src.runtime.offline import enable_offline_mode


def main() -> None:
    enable_offline_mode()
    backend, engine = create_engine()
    app = App(
        pipeline=Pipeline(FfmpegDspEnhancer(), engine),
        model_id=engine.model_id,
        enhancer_name="ffmpeg-dsp",
        backend=backend,
    )
    serve(
        app,
        host=os.environ.get("WEB_HOST", "0.0.0.0"),
        port=int(os.environ.get("WEB_PORT", str(DEFAULT_PORT))),
    )


if __name__ == "__main__":
    main()
