# 验收契约：web

> 功能描述来源：`docs/features/web.md`
> 设计方案来源：`docs/designs/`
> 测试名含 AC 编号是主锚点（`ac_<模块>_<编号>`，Python 带 `test_` 前缀），`feat-verify check` 据此校验失联
> `@acceptance AC-XX-0xx` 注释为可选补充，仅当测试名无法含编号时用
> SRT 下载相关验收编号已作废，不得复用

## 验收清单

| AC 编号 | 关联功能编号 | 验收项目（可观测结果） | 验收手段 | 验收脚本 | 测试名 |
|---|---|---|---|---|---|
| AC-WEB-001 | F-WEB-001 | GET / 返回 200 且 HTML 含文件选择、enhance 开关与提交控件 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_001` |
| AC-WEB-002 | F-WEB-002 | 页面脚本在成功响应后把 `text` 写入结果区域 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_002` |
| AC-WEB-003 | F-WEB-003 | 忙碌状态下再次提交不调用 fetch | 单元测试 | `tests/test_web_page.py` | `test_ac_web_003` |
| AC-WEB-004 | F-WEB-004 | 响应含 error 时结果区域展示该 error，不展示成功文本 | 单元测试 | `tests/test_web_page.py` | `test_ac_web_004` |
| AC-WEB-006 | F-WEB-006 | 开关关闭时请求字段 enhance=off，打开时为 on，结果区展示响应中的 enhance | 单元测试 | `tests/test_web_page.py` | `test_ac_web_006` |

## 执行记录

| 日期 | AC 编号 | 结果 | 证据 |
|---|---|---|---|
| 2026-11-26 | AC-WEB-001 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-002 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-003 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-004 | 通过 | `python3 -m unittest tests.test_web_page` |
| 2026-11-26 | AC-WEB-006 | 通过 | `python3 -m unittest tests.test_web_page` |
