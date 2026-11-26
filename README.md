# qwen3-asr-server

本机离线把音视频转成纯文本。人声增强可开关，不产出时间轴。

## 安装

只需预先安装 uv。安装脚本会按机器自动选择推理后端和 Python，并创建项目虚拟环境：

- Apple Silicon（M1/M2/M3/M4 等）：使用 MLX 4-bit；已有 Python ≥3.12 时直接复用，不降级。模型通过 ModelScope 下载 [aufklarer/Qwen3-ASR-0.6B-MLX-4bit](https://www.modelscope.cn/models/aufklarer/Qwen3-ASR-0.6B-MLX-4bit) 到 `models/Qwen3-ASR-0.6B-MLX-4bit`。
- 其它平台：使用 Python 3.12、torch + qwen-asr，并下载 `Qwen/Qwen3-ASR-0.6B` 到 `models/Qwen3-ASR-0.6B`。

```bash
./tools/setup.sh
./tools/setup.sh --check
```

ffmpeg 不在 PATH 时，脚本会下载对应架构的静态二进制到 `bin/`。`./tools/setup.sh --check` 会同时检查当前后端依赖和本地模型。

指定的 MLX 仓库原生面向 Swift，缺少 Python 特征提取元数据；安装脚本会补入与 Qwen3-ASR 原模型一致的 `preprocessor_config.json`，模型权重仍完全来自上述 ModelScope 地址。

后端默认值是 `auto`。需要手动切换时可设置 `QWEN_ASR_BACKEND=mlx|torch`；也可通过 `QWEN_ASR_MODEL=/本地模型目录` 覆盖模型路径。服务启动后保持离线，不会在首次转写时临时联网下载模型。

已有 `.venv` 会先检查 Python 版本；版本不兼容或环境损坏时停止并提示，原目录保留，不会自动删除或覆盖。`--check` 只校验解释器和依赖，不执行安装。

## 启动

```bash
./web_launch.sh
```

浏览器打开 `http://<本机IP>:11868/`。终端会打印「启动成功」。端口已被占用时会直接说明并退出。拖入音视频后转写，结果可复制。缺包时页面仍可打开，转写会说明缺什么。

## 不启动服务，直接转写

```bash
./tools/transcribe.sh /path/to/audio.mp4
./tools/transcribe.sh "./语音 样例.wav" --enhance off
./tools/transcribe.sh ./audio.wav --language Chinese > transcript.txt
```

脚本不监听端口，完成后退出。默认开启人声增强、自动识别语言；`--language` 使用模型支持的语言名，例如 `Chinese`、`English`。最终纯文本写入标准输出，进度和错误写入标准错误，失败返回非零退出码。相对输入路径以调用脚本时的目录为准，可从任意目录调用。

默认模型与后端和网页服务一致：Apple Silicon 使用本地 MLX 4-bit 模型，其它平台使用 torch 模型。可用 `QWEN_ASR_MODEL=/path/to/model ./tools/transcribe.sh audio.wav` 指定其他本地模型，不下载模型。缺少文件或参数非法时，不加载模型。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 模型、推理后端、离线状态和 ffmpeg / MLX / torch 能力是否就绪 |
| POST | `/api/transcribe` | multipart：`file`，`enhance` 为 `on` 或 `off`，缺省 `on` |

成功响应：`{"text","language","enhance"}`。
