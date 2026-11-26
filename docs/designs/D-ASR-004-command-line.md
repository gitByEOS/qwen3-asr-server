# D-ASR-004 单文件离线转写

## 目标与边界

复用既有预处理和文本引擎，提供一次执行、完成退出的命令行入口。不监听端口，不导入 HTTP 服务，不新增依赖，不生成时间轴，不写入历史记录。

## 接口

```bash
./tools/transcribe.sh input.mp4
./tools/transcribe.sh "语音 样例.wav" --enhance off
./tools/transcribe.sh input.wav --language Chinese > transcript.txt
```

| 输入 | 行为 |
|---|---|
| file | 必须是现有普通文件，按调用者工作目录解释相对路径 |
| --enhance | on 或 off，默认 on |
| --language | 默认 auto；可指定模型支持的语言名 |
| QWEN_ASR_MODEL | 默认使用当前平台后端的项目本地 0.6B，可显式覆盖为其他本地模型 |
| QWEN_ASR_BACKEND | 默认 auto；Apple Silicon 选 MLX，其它平台选 torch |

## 链路

```text
tools/transcribe.sh → src.cli 参数校验 → 离线模式 → 自动选择 ASR 后端
                  → Pipeline → FfmpegDspEnhancer → Qwen3-ASR MLX/torch
                  → stdout 最终文本 → 卸载模型 → 退出
```

`src.cli` 是与 `src.__main__` 并列的装配根，不放入 `src.entry`，避免入口协议层直接依赖音频或模型实现。脚本优先使用项目虚拟环境，前置项目 bin，不切换调用者目录。

## 输出与副作用

| 项目 | 约束 |
|---|---|
| stdout | 仅最终纯文本，附一行换行，可重定向保存 |
| stderr | 进度、依赖日志与错误 |
| 返回码 | 成功 0，转写失败 1，参数或文件校验失败 2 |
| 模型 | 参数校验后才创建，推理结束或出错均释放 |
| 输入文件 | 保留原文件，复用 Pipeline 清理生成的切片 |
| 网络 | 启动离线模式，不下载模型，不启动 HTTP |

## 验证

`tests/test_cli.py` 验证参数、单次调用、stdout/stderr 隔离、错误退出、模型释放、HTTP 模块未导入、空格路径、异地执行与模型覆盖。真实模型准确率不以替身测试代替。
