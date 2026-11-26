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

## 远期规划
- GPU 人声分离
- 浏览器麦克风
- 默认 1.7B

## 确认不做
- ForcedAligner 与 SRT
- 一次请求双次 ASR
- 服务内 CER
- import learn/whisperjav
