# 验收契约：asr

> 功能描述来源：`docs/features/asr.md`
> 设计方案来源：`docs/designs/`
> 测试名含 AC 编号是主锚点（`ac_<模块>_<编号>`，Python 带 `test_` 前缀），`feat-verify check` 据此校验失联
> `@acceptance AC-XX-0xx` 注释为可选补充，仅当测试名无法含编号时用
> AC-ASR-006、AC-ASR-007 已随时间轴需求放弃，编号作废不得复用

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

## 执行记录

| 日期 | AC 编号 | 结果 | 证据 |
|---|---|---|---|
| 2026-11-26 | AC-ASR-001 | 未执行 | 方案待确认，尚未写测试 |
| 2026-11-26 | AC-ASR-002 | 未执行 | 方案待确认，尚未写测试 |
| 2026-11-26 | AC-ASR-003 | 未执行 | 方案待确认，尚未写测试 |
| 2026-11-26 | AC-ASR-004 | 未执行 | 方案待确认，尚未写测试 |
| 2026-11-26 | AC-ASR-005 | 未执行 | 方案待确认，尚未写测试 |
| 2026-11-26 | AC-ASR-008 | 未执行 | 方案待确认，尚未写测试 |
| 2026-11-26 | AC-ASR-009 | 未执行 | 方案待确认，尚未写测试 |
