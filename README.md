# qwen3-asr-server

本机离线把音视频转成纯文本，可开关人声增强，不生成字幕或时间轴

## 安装

先安装 [uv](https://docs.astral.sh/uv/)，再执行：

```bash
./tools/setup.sh
./tools/setup.sh --check
```

脚本自动准备 Python、依赖和模型，首次安装需要联网；转写时不下载模型。已有虚拟环境不兼容时会提示并保留原目录，不会自动删除

## 网页转写

```bash
./web_launch.sh
```

看到「启动成功」后，打开 `http://<本机IP>:11868/`，选择或拖入音视频，点击转写，完成后可复制结果。端口被占用时会提示并退出

## 命令行转写

```bash
./tools/transcribe.sh /path/to/audio.mp4
./tools/transcribe.sh "./语音 样例.wav" --enhance off
./tools/transcribe.sh ./audio.wav --language Chinese > transcript.txt
```

默认开启人声增强、自动识别语言；`--enhance off` 关闭增强，`--language Chinese` 指定中文。最终文本写入标准输出，进度和错误写入标准错误，失败返回非零退出码

脚本不启动服务，完成后退出，保留原文件。可从任意目录调用；相对输入路径以调用时的目录为准，支持空格路径

## 选择后端与模型

| 平台 | 默认后端 |
|---|---|
| Apple Silicon（M 系列） | MLX 4-bit |
| Intel Mac、Linux 等其它平台 | torch |

网页和命令行默认自动选择。需要覆盖时，设置 `QWEN_ASR_BACKEND` 为 `auto`、`mlx` 或 `torch`，用 `QWEN_ASR_MODEL=/本地模型目录` 指定模型；自定义模型须与所选后端匹配

## HTTP 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 查看后端、模型、依赖与忙碌状态 |
| POST | `/api/transcribe` | 上传文件；multipart 字段为 `file`、`language`、`enhance` |
| GET | `/api/events` | 接收进度与累计正文 |

转写成功返回 `text`、`language`、`enhance`；字段默认值见[接口说明](docs/designs/D-ASR-001-single-process-http.md#用法与接口)，错误响应见[约束说明](docs/designs/D-ASR-001-single-process-http.md#不变量与约束)

## 使用前须知

- `--check` 通过不等于模型可用，尤其是自定义模型，仍需实际转写验证
- MLX 自动识别部分语言时可能混入内部标记，实机验证尚未覆盖
- 安装错误处理仍有缺口：MLX 下载 Python 失败后可能继续；后端只填写上述合法值，避免安装错误的依赖

技术细节与已知偏差见[服务设计](docs/designs/D-ASR-001-single-process-http.md)，刷新行为见[刷新协同](docs/designs/D-ASR-002-refresh-sync.md)，音频分组见[静音切段](docs/designs/D-ASR-003-silence-split.md)，脚本参数与输出约定见[命令行设计](docs/designs/D-ASR-004-command-line.md)
