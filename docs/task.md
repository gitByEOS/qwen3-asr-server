# 任务计划

## 未领取
- [ ] TASK-002: 实现 L6 运行时离线开关与 ffmpeg 探活
- [ ] TASK-003: 实现 L3 预处理滤镜表 on 与 off
- [ ] TASK-004: 实现 L5 ASR 文本引擎与可注入替身
- [ ] TASK-005: 实现 L2 编排单飞且一次只转写一遍
- [ ] TASK-006: 实现 L1 HTTP health 与 transcribe 验收
- [ ] TASK-007: 实现 L1 网页 enhance 开关
- [ ] TASK-008: 补启动脚本并跑通 feat-verify check

## 进行中

## 已完成
- [x] TASK-001 [32de6aa]: 实现 L4 协议层 EnhanceState 与 TranscribeResult
  - 轮次1：L4 只放 EnhanceState、TranscribeResult 和引擎协议，缺省 enhance=on，非法值抛错；<dirs:tests;>

## 远期规划
- GPU 人声分离
- 浏览器麦克风
- 默认 1.7B

## 确认不做
- ForcedAligner 与 SRT
- 一次请求双次 ASR
- 服务内 CER
- import learn/whisperjav
