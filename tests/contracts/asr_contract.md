# 验收契约：asr

> 功能描述来源：`docs/features/asr.md`
> 设计方案来源：`docs/designs/`
> 测试名含 AC 编号是主锚点（`ac_<模块>_<编号>`，Python 带 `test_` 前缀），`feat-verify check` 据此校验失联
> `@acceptance AC-XX-0xx` 注释为可选补充，仅当测试名无法含编号时用
> 时间轴相关验收编号已作废，不得复用

## 验收清单

| AC 编号 | 关联功能编号 | 验收项目（可观测结果） | 验收手段 | 验收脚本 | 测试名 |
|---|---|---|---|---|---|
| AC-ASR-001 | F-ASR-001 | GET /health 返回 200，JSON 含 ok/model/enhancer/offline，测试替身记录到模型加载次数为 0 | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_001` |
| AC-ASR-002 | F-ASR-002 | POST /api/transcribe 上传合法 wav 返回 200，JSON `text` 非空、含 enhance、无 segments/srt 键 | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_002` |
| AC-ASR-003 | F-ASR-003 | 空文件、超限、错误 Content-Type、enhance=maybe 均返回 4xx 且 JSON 含 error，引擎调用次数为 0 | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_003` |
| AC-ASR-004 | F-ASR-004 | 引擎报告缓存缺失时响应含离线错误文案，测试替身网络计数器仍为 0 | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_004` |
| AC-ASR-005 | F-ASR-005 | 第一次转写阻塞期间第二次请求返回 429 且 JSON 含 error | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_005` |
| AC-ASR-008 | F-ASR-008 | 未传 enhance 或 enhance=on 时，交给 L5 的音频经过 highpass+afftdn，响应 enhance 为 on | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_008` |
| AC-ASR-009 | F-ASR-009 | enhance=off 时，交给 L5 的音频未经 highpass/afftdn，L5 调用次数为 1，响应 enhance 为 off | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_009` |
| AC-ASR-010 | F-ASR-010 | 缺 ffmpeg 时 transcribe 返回 503 且 JSON 含 error，随后 health 仍 200 | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_010` |
| AC-ASR-011 | F-ASR-011 | health JSON 含 capabilities.ffmpeg、capabilities.qwen_asr、capabilities.torch 与 missing | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_011` |
| AC-ASR-012 | F-ASR-012 | 无 ffmpeg 且 enhance=off 的 wav 返回 200 且 JSON 含 text | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_012` |
| AC-ASR-013 | F-ASR-013 | 转写后连续 5 次心跳卸载模型；中途再转写则不会在第 4 次心跳卸载 | 单元测试 | `tests/test_pipeline.py` | `test_ac_asr_013` |
| AC-ASR-014 | F-ASR-014 | on_progress 收到开始、转码中、开始处理第 1 段并带时长，并在最后收到转写文本 | 单元测试 | `tests/test_pipeline.py` | `test_ac_asr_014` |
| AC-ASR-015 | F-ASR-015 | 转写阻塞期间 health.busy 为 true，结束后为 false | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_015` |
| AC-ASR-016 | F-ASR-016 | 订阅前发出的日志会在新的 /api/events 连接里先出现 | 单元测试 | `tests/test_asr_http.py` | `test_ac_asr_016` |
| AC-ASR-017 | F-ASR-017 | 没有正文标记时交出空串，有标记时只交出标记后的文字 | 单元测试 | `tests/test_asr_engine.py` | `test_ac_asr_017` |
| AC-ASR-018 | F-ASR-018 | 10 与 12 再加后面三段收成 22 秒和 28 秒；短气口落在组的时间范围内 | 单元测试 | `tests/test_audio.py` | `test_ac_asr_018` |

## 执行记录

| 日期 | AC 编号 | 结果 | 证据 |
|---|---|---|---|
| 2026-11-26 | AC-ASR-001 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-002 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-003 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-004 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-005 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-008 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-009 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-010 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-011 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-012 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-013 | 通过 | `python3 -m unittest tests.test_pipeline` |
| 2026-11-26 | AC-ASR-014 | 通过 | `python3 -m unittest tests.test_pipeline` |
| 2026-11-26 | AC-ASR-015 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-016 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-ASR-017 | 通过 | `python3 -m unittest tests.test_asr_engine` |
| 2026-11-26 | AC-ASR-018 | 通过 | `python3 -m unittest tests.test_audio tests.test_pipeline tests.test_asr_http` |
