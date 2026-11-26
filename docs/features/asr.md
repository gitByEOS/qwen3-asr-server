# asr

## 概述

| 字段 | 说明 |
|---|---|
| 业务目标 | 本机离线把音视频转成纯文本；人声增强可关，便于对比原文转写 |
| 边界 | L2–L6 后端；不产出时间轴；不算准确率分数 |
| 关键概念 | L1–L6 隔离、离线缓存、单飞、EnhanceState、ffmpeg 滤镜表 |

## 功能清单

| 状态 | F 编号 | 可观测结果（主体在触发条件下产生） | design |
|---|---|---|---|
| ✓ | F-ASR-001 | 调用方请求 GET /health 时得到 JSON，含 ok、model、enhancer、offline，且此次调用不加载 ASR 模型 | D-ASR-001 |
| ✓ | F-ASR-002 | 调用方以 multipart 上传合法音视频到 POST /api/transcribe 时得到 JSON，`text` 非空，含 `enhance`，且不含 segments/srt | D-ASR-001 |
| ✓ | F-ASR-003 | 调用方上传空文件、超 50MB、非音视频或非法 enhance 时得到 4xx 与 JSON `error`，且不调用引擎 | D-ASR-001 |
| ✓ | F-ASR-004 | 本地模型缓存缺失时 POST /api/transcribe 得到明确离线错误，进程不发起 HuggingFace 网络请求 | D-ASR-001 |
| ✓ | F-ASR-005 | 已有转写进行中时第二次 POST /api/transcribe 得到 429 与 JSON `error` | D-ASR-001 |
| ✓ | F-ASR-008 | enhance 缺省或为 on 时，L3 对输入执行 highpass+afftdn 后再交给 L5，响应 `enhance` 为 on，health.enhancer 为 ffmpeg-dsp | D-ASR-001 |
| ✓ | F-ASR-009 | enhance 为 off 时，L3 只转 16kHz 单声道、不接高通和降噪，L5 仍被调用一次，响应 `enhance` 为 off | D-ASR-001 |
| ✓ | F-ASR-010 | 缺 ffmpeg 或 qwen-asr 时 POST /api/transcribe 返回 503 JSON error，进程继续，GET /health 仍 200 | D-ASR-001 |
| ✓ | F-ASR-011 | GET /health 的 JSON 含 backend、ffmpeg、qwen_asr_mlx、qwen_asr、torch 能力及当前后端的 missing 列表 | D-ASR-001 |
| ✓ | F-ASR-012 | 缺 ffmpeg 且 enhance=off 时，wav 直通 L5 并返回 200，不 503 | D-ASR-001 |
| ✓ | F-ASR-013 | 心跳连续 5 次且期间无 transcribe 时卸载模型；再次转写会重新加载 | D-ASR-003 |
| ✓ | F-ASR-014 | 转写过程通过 on_progress 依次回传进度，并在结束时回传转写文本 | D-ASR-001 |
| ✓ | F-ASR-015 | 转写进行中 GET /health 的 busy 为 true，结束后为 false | D-ASR-002 |
| ✓ | F-ASR-016 | 新连接 GET /api/events 先收到订阅前已发出的日志 | D-ASR-002 |
| ✓ | F-ASR-017 | 生成原文里还没有正文标记时不交出文本，出现标记后交出标记后面的字 | D-ASR-002 |
| ✓ | F-ASR-018 | 相邻原子段装箱后每组贴近 30 秒，组内气口仍留在这段音频里 | D-ASR-003 |
| ✓ | F-ASR-019 | Apple Silicon 启动时自动选择 MLX，以本地 `aufklarer/Qwen3-ASR-0.6B-MLX-4bit` 转写；其它平台保持 torch 后端 | D-ASR-001 |

## 阻塞延后

| 功能或依赖 | 阻塞原因 | 解除条件 |
|---|---|---|
| 麦克风实时录音 | v1 只做文件上传 | 上传路径验收通过后再加 |
| 1.7B 默认模型 | Mac 内存优先跑通 0.6B | 用环境变量可换，不改默认 |
| GPU 人声分离 | 与 ASR 抢显存，违反性能优先 | 用户明确要求再开新 D |
| 服务内准确率分数 | 无标注文本 | 另备标注文本后再开评测工具 |

## 明确不做

| 排除事项 | 排除原因 |
|---|---|
| 时间点与字幕文件（原 006/007） | 用户改为不要时间点，编号作废不得复用 |
| 一次请求把同一段识别两遍 | 违反性能优先 |
| 对齐 | 性能优先 |
| 翻译 | 本仓库不做 |
