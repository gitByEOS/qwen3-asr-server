# D-ASR-001 单进程离线转写服务

## 背景与目标

| 字段 | 说明 |
|---|---|
| 要解决的问题 | 本机离线把音视频转成纯文本 |
| 业务/技术背景 | 单进程网页加接口。按六层分开。人声增强走 ffmpeg 滤镜。性能优先，不要时间点 |
| 目标边界 | 后端加简单网页。人声增强可开关。只出纯文本。不要时间点、翻译。一次请求不把同一段识别两遍 |

## 关联功能

[asr](../features/asr.md)
[web](../features/web.md)

## 架构设计

### 用法与接口

| 方法 | 路径 | 输入或返回 |
|---|---|---|
| GET | `/` | 文件选择、拖入与人声增强开关 |
| GET | `/health` | 模型、后端、离线状态、依赖能力、missing 与 busy；不加载模型 |
| POST | `/api/transcribe` | multipart：file、language（默认 auto）、enhance（默认 on，仅 on / off） |
| GET | `/api/events` | SSE 推送进度、累计正文与 busy；刷新回放见 [D-ASR-002](D-ASR-002-refresh-sync.md) |

```python
# ./web_launch.sh  →  http://<局域网IP>:11868/

result = pipeline.run(audio_path, language="auto", enhance="on")
# result.text  result.language  result.enhance

# GET  /health
#   {"ok": true, "model": ".../Qwen3-ASR-0.6B-MLX-4bit", "backend": "mlx",
#    "enhancer": "ffmpeg-dsp", "offline": true,
#    "capabilities": {"ffmpeg": true, "qwen_asr_mlx": true,
#                     "qwen_asr": false, "torch": false}, "missing": [], "busy": false}
# POST /api/transcribe  multipart: file, language, enhance
#   enhance 缺省为 on；只接受 on / off
#   {"text": "...", "language": "zh", "enhance": "on"}
```

### 核心思路

**六层隔离，只出文本。** 增强与转码共用一次 ffmpeg，每个音频分组只识别一次；开关和对比方式见下方关键设计点。

### 分层与组件

```text
L1 入口 src/entry
  GET /  GET /health  POST /api/transcribe  GET /api/events  内嵌网页（enhance 开关）
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
  Apple Silicon: Qwen3-ASR 4-bit MLX；其它平台: Qwen3-ASR torch
  auto 按 Darwin/arm64 选后端，文本 only
  只依赖 L4、L6
       ▼
L6 运行时 src/runtime
  HF_HUB_OFFLINE  设备  ffmpeg 探活
  不向上依赖
```

目录即隔离：禁止 L1 import L5，禁止 L5 import L3。

启动顺序：`web_launch.sh` 设 `HF_HUB_OFFLINE=1` → 起 L1 → 首次转写才加载 L5 模型。

```text
上传文件 + enhance
 → L1 校验 → L2 单飞（on_progress / on_partial → SSE /api/events）
 → L3 有 ffmpeg：转码（on 再滤镜）；无 ffmpeg：wav+off 直通，否则 503
 → L5 按平台使用 Qwen3-ASR MLX 或 torch 后端；当前后端缺依赖时 503
 → {text, language, enhance} 或缺包 JSON error
```

### 关键设计点

| 设计点 | 是什么 | 为什么这么定 |
|---|---|---|
| L1–L6 目录隔离 | 一层一个包，依赖只向下 | 入口不碰模型和转码 |
| 不要时间点 | 不做对齐 | 性能优先 |
| EnhanceState | 唯一字段 `on` / `off`，缺省 `on` | 消灭多个 bool；非法值 400 |
| 滤镜表 | `{"off": [aformat], "on": [aformat, highpass, afftdn]}` | 同一条 ffmpeg，不写两条路径 |
| 对比准确率 | 两次请求，人工看两段 text | 一次请求不把同一段识别两遍；无标注不算分数 |
| 人声增强 | L3 `ffmpeg-dsp`，不占 GPU | 要增强但不抢 ASR 显存 |
| 单进程 | L1 网页与 API 同进程 | 没有现成模型 HTTP |
| 返回体 | `text`、`language`、`enhance` | 回显开关，无时间轴 |
| 通用模型 | `Qwen/Qwen3-ASR-0.6B` | 非 Apple Silicon 平台保持原 torch 路径 |
| M 芯片模型 | `aufklarer/Qwen3-ASR-0.6B-MLX-4bit` | 4-bit 约 680MB，使用统一内存与 Metal |
| 后端选择 | `auto` 在 Darwin arm64 选 MLX，其它平台选 torch；环境变量可覆盖 | M 芯片无需安装 torch，旧平台不受影响 |
| MLX 生成保护 | 每段默认最多生成 2048 tokens；尾部内容连续重复 8 次时提前结束；结束后关闭生成流并清理上下文，保留模型权重 | 无结束标记或重复解码不能长期占住单飞锁；下一段不继承上一段状态 |
| 离线 | 启动即 `HF_HUB_OFFLINE=1` | 缺缓存直接报错 |
| 缺包不崩 | L6 只探活不导入；缺项进 health.missing；请求 503 | 进程要继续给人看网页 |
| 网页拖入 | 文档级 dragenter/drop 写入 file input | 文件选择和拖入走同一个 input |
| 单飞 | L2 同时只跑一条 | 模型占内存 |
| 进度回传 | GET /api/events SSE；on_progress 推日志，on_partial 推累计正文 | POST 会等待冷启动和推理，进度需独立通道 |

### 安装本地模型

`tools/setup.sh` 通过 uv 创建环境，并从 ModelScope 下载当前平台的默认模型：

| 平台 | Python 选择 | 模型来源 → 本地目录 |
|---|---|---|
| Darwin arm64 | 新建环境时优先复用已有 Python ≥3.12，否则由 uv 准备 3.12；已有 `.venv` 也须满足最低版本 | [aufklarer/Qwen3-ASR-0.6B-MLX-4bit](https://www.modelscope.cn/models/aufklarer/Qwen3-ASR-0.6B-MLX-4bit) → `models/Qwen3-ASR-0.6B-MLX-4bit` |
| 其它平台 | Python 3.12；已有 `.venv` 版本必须匹配 | `Qwen/Qwen3-ASR-0.6B` → `models/Qwen3-ASR-0.6B` |

版本不兼容或环境损坏时保留原目录并报错，不自动重建。ffmpeg 不在 PATH 时下载对应架构的静态二进制到 `bin/`。

指定 MLX 仓库原生面向 Swift，缺少 Python 特征提取元数据；脚本从 `tools/mlx_preprocessor_config.json` 补入 `preprocessor_config.json`，权重仍来自上表仓库。网页与命令行按同一后端选择默认目录，运行时可用 `QWEN_ASR_MODEL` 覆盖。

## 被排除方案

| 方案 | 排除原因 |
|---|---|
| 一次请求双跑原声+增强 | 违反性能优先 |
| 服务内计算准确率分数 | 无标注，ffmpeg 也不是分离器 |
| 对齐与字幕文件 | 用户不要时间点 |
| 独立的人声分离模型 | 与转写抢显存 |
| 模型服务与网页拆成两个进程 | 没有现成模型服务 |
| FastAPI / Flask | 标准库 HTTP 已覆盖 |

## 不变量与约束

| 类型 | 内容 |
|---|---|
| 不变量 | 转写结果不含时间轴 |
| 不变量 | 转 16kHz 与可选增强在同一次 ffmpeg 中完成 |
| 不变量 | 没有静音切段时，一次运行只解析一次 |
| 不变量 | 同一时刻最多一个 `pipeline.run` |
| 约束 | 上传上限 50MB；缺包或缺缓存 503，进程不退出 |
| 约束 | MLX 后端只加载 setup 下载的本地模型目录，不在请求期间访问网络 |
| 约束 | MLX 的 2048 tokens 是每段默认生成上限，不是整个请求的文本上限；正常生成遇到结束标记即停止 |
| 约束 | 无 ffmpeg 时仅 wav + enhance=off 可直通 |
| 边界条件 | 空文件、非音视频、超限、非法 enhance 一律 4xx JSON `{"error": "..."}` |
| 隔离 | L1 不得 import L5；L5 不得 import L3；测试按层注入替身 |

## 评审记录

| 日期 | 评审结论 | 备注 |
|---|---|---|
| 2026-11-26 | 修订 | 去掉时间点；分层隔离；预处理增强 |
| 2026-11-26 | 修订 | 增加 enhance on/off|
| 2026-11-26 | 修订 | 缺包不崩、health 探活、网页拖入 |
| 2026-11-26 | 修订 | SSE 进度日志 |
| 2026-11-27 | 修订 | MLX 增加生成上限、重复熔断与逐段上下文清理 |

## 实现偏差与验证范围

设计要求保持不变，以下是当前实现缺口，不是已放宽的约束：

| 设计要求 | 当前实现 |
|---|---|
| 非音视频返回 4xx | ffmpeg 解码失败进入通用异常分支，返回 500 |
| 转写只交出正文 | MLX 自动识别 Cantonese、Macedonian 时可能泄漏 `<asr_text>`，语言仍为 auto |
| 自检检查实际转写所用模型 | `setup --check` 忽略 `QWEN_ASR_MODEL`，仍检查默认目录 |
| 模型不完整时自检失败 | 仅检查 `config.json`，MLX 另查 `preprocessor_config.json` 是否存在；不验证内容、权重或分词器，空配置也可能通过 |
| 解释器准备失败立即停止 | MLX 分支下载 Python 失败后仍可能继续执行查找和创建环境 |
| 非法后端在安装前拒绝 | 非法值可能先进入 torch 依赖安装，最后才失败 |

`setup --check` 还会校验解释器版本与当前后端依赖，不执行安装；它与 `/health` 都不能代替实际转写验证。

接口与测试锚点见 [ASR 契约](../../tests/contracts/asr_contract.md)，Intel torch 短样本结果见其[人工实测记录](../../tests/contracts/asr_contract.md#人工实测记录)。替身测试不等于 MLX 实机推理或准确率通过。
