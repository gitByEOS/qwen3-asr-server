# D-ASR-001 单进程离线转写服务

## 背景与目标

| 字段 | 说明 |
|---|---|
| 要解决的问题 | WhisperJAV 把 Qwen3-ASR 埋在字幕管线里，无法当本地转写服务用 |
| 业务/技术背景 | 参考 `../fany` 的网页形态；参考 `./learn` 的 L1–L6 分层与 ffmpeg 人声向 DSP。性能优先，不要时间戳 |
| 目标边界 | 后端 + 简单网页。人声增强可开关。只出纯文本。不要对齐器、SRT、VAD、场景、翻译、Ensemble、双次 ASR |

## 关联功能

[asr](../features/asr.md)
[web](../features/web.md)

## 架构设计

### 用法与接口

```python
# ./web_launch.sh  →  http://<局域网IP>:11801/

result = pipeline.run(audio_path, language="auto", enhance="on")
# result.text  result.language  result.enhance

# GET  /health
#   {"ok": true, "model": "Qwen/Qwen3-ASR-0.6B", "enhancer": "ffmpeg-dsp", "offline": true,
#    "capabilities": {"ffmpeg": false, "qwen_asr": false, "torch": false},
#    "missing": ["ffmpeg", "qwen_asr", "torch"]}
# POST /api/transcribe  multipart: file, language, enhance
#   enhance 缺省为 on；只接受 on / off
#   {"text": "...", "language": "zh", "enhance": "on"}
```

### 核心思路

**按 L1–L6 隔离，只出文本；增强是同一条 ffmpeg 路上的滤镜表，不是第二条 ASR。** `enhance` 用一个状态 `on|off`。两次人工对比靠两次请求，不当场算准确率。

### 分层与组件

```text
L1 入口 src/entry
  GET /  GET /health  POST /api/transcribe  内嵌网页（enhance 开关）
  只依赖 L2
       ▼
L2 编排 src/pipeline
  单飞锁 → L3.prepare(enhance) → L5.transcribe
  只依赖 L3、L5、L4
       ▼
L3 预处理 src/audio
  一次 ffmpeg：16kHz 单声道 + 滤镜表[enhance]
  只依赖 L4、L6
       ▼
L4 协议 src/protocol
  SpeechEnhancer  AsrEngine  TranscribeResult  EnhanceState
  不依赖其它层
       ▼
L5 ASR src/asr
  Qwen3ASRModel.transcribe  文本 only
  只依赖 L4、L6
       ▼
L6 运行时 src/runtime
  HF_HUB_OFFLINE  设备  ffmpeg 探活
  不向上依赖
```

目录即隔离：禁止 L1 import L5，禁止 L5 import L3，禁止任何层 import `learn/`。

启动顺序：`web_launch.sh` 设 `HF_HUB_OFFLINE=1` → 起 L1 → 首次转写才加载 L5 模型。

```text
上传文件 + enhance
 → L1 校验 → L2 单飞（on_progress → SSE /api/events）
 → L3 有 ffmpeg：转码（on 再滤镜）；无 ffmpeg：wav+off 直通，否则 503
 → L5 有 qwen-asr：转写；无：503
 → {text, language, enhance} 或缺包 JSON error
心跳 30s × 5 次无 transcribe → L5.release 卸模型
```

### 关键设计点

| 设计点 | 是什么 | 为什么这么定 |
|---|---|---|
| L1–L6 目录隔离 | 一层一个包，依赖只向下 | 按原分层代号隔离 |
| 不要时间戳 | 不加载 ForcedAligner | 性能优先 |
| EnhanceState | 唯一字段 `on` / `off`，缺省 `on` | 消灭多个 bool；非法值 400 |
| 滤镜表 | `{"off": [aformat], "on": [aformat, highpass, afftdn]}` | 同一条 ffmpeg，不写两条路径 |
| 对比准确率 | 两次请求，人工看两段 text | 一次请求不跑两遍 ASR；无标注不算 CER |
| 人声增强 | L3 `ffmpeg-dsp`，不占 GPU | 要增强但不抢 ASR 显存 |
| 单进程 | L1 网页与 API 同进程 | 没有现成模型 HTTP |
| 返回体 | `text`、`language`、`enhance` | 回显开关，无时间轴 |
| 默认模型 | `Qwen/Qwen3-ASR-0.6B` | Mac 先跑通 |
| 离线 | 启动即 `HF_HUB_OFFLINE=1` | 缺缓存直接报错 |
| 缺包不崩 | L6 只探活不导入；缺项进 health.missing；请求 503 | 进程要继续给人看网页 |
| 网页拖入 | 文档级 dragenter/drop 写入 file input | 参考 videoya 拖入区 |
| 单飞 | L2 同时只跑一条 | 模型占内存 |
| 进度回传 | GET /api/events SSE，L2 on_progress 推 log | POST 会堵在冷启动，进度必须另开通道 |
| 空闲卸载 | 30s 心跳，连续 5 次无 transcribe 则 release | 解放内存，下次冷启动 |
| 不引用 learn | `learn/` 只读 | 禁止 import whisperjav |

## 被排除方案

| 方案 | 排除原因 |
|---|---|
| 一次请求双跑原声+增强 | 违反性能优先 |
| 服务内计算 CER / SI-SDR | 无标注、ffmpeg 也不是分离器 |
| ForcedAligner / SRT | 用户不要时间戳 |
| Demucs / ZipEnhancer / RoFormer | 与 ASR 抢 GPU |
| 复用 WhisperJAV QwenPipeline | 9 阶段字幕管线 |
| 场景检测 / VAD | 无字幕时间轴 |
| fany 式双进程 | 没有现成模型服务 |
| FastAPI / Flask | 标准库 HTTP 已覆盖 |

## 不变量与约束

| 类型 | 内容 |
|---|---|
| 不变量 | 转写结果不含时间轴 |
| 不变量 | 转 16kHz 与可选增强在同一次 ffmpeg 中完成 |
| 不变量 | 一次 `pipeline.run` 只调用一次 L5 |
| 不变量 | 同一时刻最多一个 `pipeline.run` |
| 约束 | 上传上限 50MB；缺包或缺缓存 503，进程不退出 |
| 约束 | 无 ffmpeg 时仅 wav + enhance=off 可直通 |
| 边界条件 | 空文件、非音视频、超限、非法 enhance 一律 4xx JSON `{"error": "..."}` |
| 隔离 | L1 不得 import L5；L5 不得 import L3；测试按层注入替身 |

## 评审记录

| 日期 | 评审结论 | 备注 |
|---|---|---|
| 2026-11-26 | 修订 | 去掉对齐器与 SRT；L1–L6 隔离；L3 增强 |
| 2026-11-26 | 修订 | 增加 enhance on/off|
| 2026-11-26 | 修订 | 缺包不崩、health 探活、网页拖入 |
| 2026-11-26 | 修订 | SSE 进度日志；30s×5 空闲卸模型 |
