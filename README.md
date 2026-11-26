# qwen3-asr-offline

本机离线把音视频转成纯文本。人声增强可开关，不产出时间轴。

## 安装

需要 Python 3.12 和 uv。Intel Mac 的 Python 3.13 没有 torch 轮子。

```bash
./tools/setup.sh
./tools/setup.sh --check
```

脚本用清华源安装 torch、qwen-asr，并用魔搭下载 `Qwen/Qwen3-ASR-0.6B` 到 `models/Qwen3-ASR-0.6B`。ffmpeg 不在 PATH 时会下载静态二进制到 `bin/`。

## 启动

```bash
./web_launch.sh
```

浏览器打开 `http://<本机IP>:11801/`。拖入音视频后转写，结果可复制。缺包时页面仍可打开，转写会说明缺什么。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 模型、离线状态、ffmpeg / qwen_asr / torch 是否就绪 |
| POST | `/api/transcribe` | multipart：`file`，`enhance` 为 `on` 或 `off`，缺省 `on` |

成功响应：`{"text","language","enhance"}`。
