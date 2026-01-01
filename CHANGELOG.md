# 更新日志 (Changelog)

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-01-02

### 里程碑：语音对话版完成

首个可用版本，实现了完整的语音对话功能。

### 新增
- **语音对话流程**
  - K230录音（4秒）
  - HTTP上传音频到服务器
  - 阿里云Paraformer语音识别(ASR)
  - 通义千问大模型对话(LLM)
  - Edge-TTS语音合成
  - K230下载并播放回复

- **桌宠表情系统**
  - 眨眼动画（随机间隔2.5-5秒）
  - 呼吸动画（正弦波Y轴偏移）
  - 说话动画（嘴型开合）
  - 多种表情：neutral, happy, sleepy, listening, thinking, talking

- **服务器端**
  - Flask REST API
  - `/chat/audio` - 语音对话接口
  - `/ping` - 心跳测试
  - `/test_audio` - TTS测试
  - `/test_asr` - ASR测试

- **网络模块**
  - 原生socket实现HTTP (无urequests)
  - 大文件分块发送
  - 超时重试机制

### 技术突破
- 解决K230 Display与Audio共用MediaManager冲突
- 解决170KB音频HTTP上传问题
- 解决WiFi在Display.deinit后中断问题

### 已知限制
- 录音/播放时屏幕会关闭（硬件限制）
- 仅支持2.4GHz WiFi
- 仅支持WAV音频格式

---

## 开发中功能

### 视觉感知版（规划中）
- 人脸检测 + 头部朝向
- 眼睛跟随用户
- 根据用户注视状态切换表情
- 结合语音的多模态交互

---

## 开发历程

### 2026-01-02
- 09:00 - 决定采用"边缘设备+网关"架构
- 10:00 - K230 WiFi连接测试成功
- 11:00 - HTTP GET/POST测试成功
- 12:00 - 图片上传测试成功
- 14:00 - 音频录制测试成功（解决MediaManager问题）
- 15:00 - 音频播放测试成功
- 16:00 - 服务器接入通义千问LLM
- 17:00 - 服务器接入Edge-TTS
- 18:00 - 服务器接入Paraformer ASR
- 20:00 - 整合主程序，解决Display/Audio冲突
- 21:00 - 完整语音对话流程测试成功！
