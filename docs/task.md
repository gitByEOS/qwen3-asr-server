# 任务计划

## 未领取

## 进行中

## 已完成
- [x] TASK-001 [32de6aa]: 实现 L4 协议层 EnhanceState 与 TranscribeResult
  - 轮次1：L4 只放 EnhanceState、TranscribeResult 和引擎协议，缺省 enhance=on，非法值抛错；<dirs:tests;>
- [x] TASK-002 [3230d37]: 实现 L6 运行时离线开关与 ffmpeg 探活
  - 轮次1：L6 只设 HF 离线环境变量并用 which 探活 ffmpeg，不转码不加载模型；<dirs:src;tests;>
- [x] TASK-003 [e5903ee]: 实现 L3 预处理滤镜表 on 与 off
  - 轮次1：L3 用滤镜表驱动一次 ffmpeg：off 只转 16kHz，on 再接高通和降噪；<dirs:src;tests;>
- [x] TASK-004 [567bb0a]: 实现 L5 ASR 文本引擎与可注入替身
  - 轮次1：L5 用注入的 load_model 懒加载，模块导入不碰 qwen_asr，缺缓存只抛 OfflineError；<dirs:src;tests;>
- [x] TASK-005 [3f0d45c]: 实现 L2 编排单飞且一次只转写一遍
  - 轮次1：L2 非阻塞锁实现单飞，一次 run 只调一次引擎，enhance 原样交给 L3；<dirs:src;tests;>
- [x] TASK-006 [3d11ceb]: 实现 L1 HTTP health 与 transcribe 验收
  - 轮次1：L1 只提供 health 与 transcribe，AC-ASR 用替身跑通，health 不加载模型；<dirs:docs;src;tests;>
- [x] TASK-007 [d1f5ea7]: 实现 L1 网页 enhance 开关
  - 轮次1：L1 内嵌转写页，enhance 勾选对应 on/off，忙碌时直接 return 不发第二次请求；<dirs:docs;src;tests;>
- [x] TASK-008 [2f623ea]: 补启动脚本并跑通 feat-verify check
  - 轮次1：补 web_launch 与装配入口，feat-verify 12 个 AC 锚点完整，L1 不引用 L3/L5；<dirs:docs;src;tests;web_launch.sh;>
- [x] TASK-009 [2bc5a7e]: 写 tools/setup.sh，在本机补齐 ffmpeg、qwen_asr、torch，并用 --check 验收完备
  - 轮次1：用 uv 走清华源装包、魔搭拉 0.6B，setup --check 三项就绪；<dirs:docs;src;tests;tools;web_launch.sh;>
- [x] TASK-010 [cb3c4bf]: 写刷新后网页与后端协同设计，并实现状态同步
  - 轮次1：刷新后用 health.busy 和日志回放接上转写，文件不能恢复；<dirs:README.md;docs;src;tests;>
- [x] TASK-011 [8131d28]: 按 D-ASR-003 先扫静音、归并、切分后再解析
  - 轮次1：先扫静音再归并，短间隔留在人声段里，按段解析并拼接；<dirs:docs;src;tests;>
- [x] TASK-012 [cbd2807]: 修复推送前审查的占锁、短有声丢样和装箱性能问题，并提供 tools 无 server 转写脚本
  - 轮次1：清理异常始终释放单飞锁并保留所有非空有声采样，精确剪枝保持装箱目标，新增离线单文件脚本且标准输出仅含文本，82项测试和29个契约锚点通过；<dirs:README.md;docs;src;tests;tools;>
- [x] TASK-013 [cbd2807]: 由 setup 自动准备 Python 3.12 并校验已有环境，消除 README 中 Intel Mac 的手动注意事项
  - 轮次1：安装脚本统一准备和校验Python3.12，拒绝并保留不兼容或损坏环境，解释器下载失败立即停止，README无需手动选择Python，11项安装回归与93项全量测试通过；<dirs:README.md;docs;src;tests;tools;>
- [x] TASK-014 [f166c44]: 补齐 Apple Silicon MLX 4-bit 推理支持
  - 轮次1：Darwin arm64 自动选择 MLX，从魔搭下载 aufklarer 4-bit 模型；其它平台保持 torch；<dirs:docs;src;tests;tools;web_launch.sh;>
- [x] TASK-015 [48887ff]: 实测本机真实离线转写，并按莱特规范精简说明文档，提高人类可读性
  - 轮次1：派出莱特规范化README与四份设计且保留命令接口约束与已知缺陷，36项相关测试和30个锚点通过；<dirs:README.md;docs;>
- [x] TASK-016 [48887ff]: 根据记忆重新梳理REAME写法与职责
  - 轮次1：README仅保留快速入门和简短使用限制，技术说明归入原设计规范，真实转写证据归入验收记录，链接规范及30锚点完整且8项CLI测试通过；<dirs:README.md;docs;tests;>

## 远期规划
- GPU 人声分离
- 浏览器麦克风
- 默认 1.7B

## 确认不做
- 对齐与字幕文件
- 一次请求把同一段识别两遍
- 服务内准确率分数
