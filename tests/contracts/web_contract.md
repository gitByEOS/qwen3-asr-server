# 验收契约：web

> 功能描述来源：`docs/features/web.md`
> 设计方案来源：`docs/designs/`
> 测试名含 AC 编号是主锚点（`ac_<模块>_<编号>`，Python 带 `test_` 前缀），`feat-verify check` 据此校验失联
> `@acceptance AC-XX-0xx` 注释为可选补充，仅当测试名无法含编号时用
> 字幕文件下载相关验收编号已作废，不得复用

## 验收清单

| AC 编号 | 关联功能编号 | 验收项目（可观测结果） | 验收手段 | 验收脚本 | 测试名 |
|---|---|---|---|---|---|
| AC-WEB-001 | F-WEB-001 | GET / 返回 200 且 HTML 含文件选择、enhance 开关与提交控件 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_001` |
| AC-WEB-002 | F-WEB-002 | 页面脚本在成功响应后把 `text` 写入结果区域 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_002` |
| AC-WEB-003 | F-WEB-003 | 忙碌状态下再次提交不调用 fetch | 单元测试 | `tests/test_web_page.py` | `test_ac_web_003` |
| AC-WEB-004 | F-WEB-004 | 响应含 error 时结果区域展示该 error，不展示成功文本 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_004` |
| AC-WEB-006 | F-WEB-006 | 开关关闭时请求字段 enhance=off，打开时为 on，结果区展示响应中的 enhance | 单元测试 | `tests/test_web_page.py` | `test_ac_web_006` |
| AC-WEB-007 | F-WEB-007 | 页面含 drop-zone，脚本处理 drag-over 与 dataTransfer.files | 单元测试 | `tests/test_web_page.py` | `test_ac_web_007` |
| AC-WEB-008 | F-WEB-008 | 页面脚本读取 health.missing 并展示 warning | 单元测试 | `tests/test_web_page.py` | `test_ac_web_008` |
| AC-WEB-009 | F-WEB-009 | 页面含 id=log，脚本创建 EventSource 监听 /api/events | 单元测试 | `tests/test_web_page.py` | `test_ac_web_009` |
| AC-WEB-010 | F-WEB-010 | 订阅 /api/events 后发起转写，事件流含进度 log 与转写文本 | 单元测试 | `tests/test_asr_http.py` | `test_ac_web_010` |
| AC-WEB-011 | F-WEB-011 | 页面脚本在 health.busy 时禁用提交按钮 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_011` |
| AC-WEB-012 | F-WEB-012 | 无文件提交时结果区写入请先拖入，且该判断位于 fetch 之前 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_012` |
| AC-WEB-013 | F-WEB-013 | 事件回调里把 data.text 写入结果区 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_013` |

## 执行记录

| 日期 | AC 编号 | 结果 | 证据 |
|---|---|---|---|
| 2026-11-26 | AC-WEB-001 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-002 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-003 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-004 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-006 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-007 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-008 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-009 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-010 | 通过 | `python3 -m unittest tests.test_asr_http` |
| 2026-11-26 | AC-WEB-011 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-012 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-013 | 通过 | `python3 -m unittest tests.test_web_page` |
