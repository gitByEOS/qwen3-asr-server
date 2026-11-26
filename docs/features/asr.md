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
| × | F-ASR-001 | 调用方请求 GET /health 时得到 JSON，含 ok、model、enhancer、offline，且此次调用不加载 ASR 模型 | D-ASR-001 |
| × | F-ASR-002 | 调用方以 multipart 上传合法音视频到 POST /api/transcribe 时得到 JSON，`text` 非空，含 `enhance`，且不含 segments/srt | D-ASR-001 |
| × | F-ASR-003 | 调用方上传空文件、超 50MB、非音视频或非法 enhance 时得到 4xx 与 JSON `error`，且不调用引擎 | D-ASR-001 |
| × | F-ASR-004 | 本地模型缓存缺失时 POST /api/transcribe 得到明确离线错误，进程不发起 HuggingFace 网络请求 | D-ASR-001 |
| × | F-ASR-005 | 已有转写进行中时第二次 POST /api/transcribe 得到 429 与 JSON `error` | D-ASR-001 |
| × | F-ASR-008 | enhance 缺省或为 on 时，L3 对输入执行 highpass+afftdn 后再交给 L5，响应 `enhance` 为 on，health.enhancer 为 ffmpeg-dsp | D-ASR-001 |
| × | F-ASR-009 | enhance 为 off 时，L3 只转 16kHz 单声道、不接高通和降噪，L5 仍被调用一次，响应 `enhance` 为 off | D-ASR-001 |

## 阻塞延后

| 功能或依赖 | 阻塞原因 | 解除条件 |
|---|---|---|
| 麦克风实时录音 | v1 只做文件上传 | 上传路径验收通过后再加 |
| 1.7B 默认模型 | Mac 内存优先跑通 0.6B | 用环境变量可换，不改默认 |
| GPU 人声分离 | 与 ASR 抢显存，违反性能优先 | 用户明确要求再开新 D |
| 服务内 CER | 无标注文本 | 另备金标后再开评测工具 |

## 明确不做

| 排除事项 | 排除原因 |
|---|---|
| F-ASR-006 / F-ASR-007 时间轴与 SRT | 用户改为不要时间戳，编号作废不得复用 |
| 一次请求跑两遍 ASR | 违反性能优先 |
| ForcedAligner | 性能优先 |
| 场景切分 / VAD | 无字幕时间轴 |
| 翻译 | 本仓库不做 |
