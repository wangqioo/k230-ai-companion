# K230 桌面宠物 (Desktop Pet)

基于嘉楠K230开发板的AI语音交互桌面宠物项目。

## 项目简介

这是一个运行在庐山派K230开发板上的桌面宠物，支持：
- 语音对话：通过麦克风录音，AI理解并语音回复
- 表情动画：可爱的眨眼、呼吸、说话动画
- 视觉感知：人脸检测和头部朝向跟踪（视觉版）

## 系统架构

```
┌─────────────────┐         ┌─────────────────────┐
│   K230开发板     │  HTTP   │    PC服务器          │
│                 │ ──────> │                     │
│ - 录音/播放     │         │ - ASR语音识别        │
│ - 表情显示      │ <────── │ - LLM对话(通义千问)  │
│ - WiFi通信      │  音频   │ - TTS语音合成        │
└─────────────────┘         └─────────────────────┘
```

采用"边缘设备 + 网关"架构，因为K230不支持TLS/WSS，无法直接调用云端API。

## 硬件要求

- **开发板**: 庐山派K230 CanMV开发板
- **显示屏**: 3.1寸LCD扩展板 (800x480)
- **音频**: 板载麦克风 + 3.5mm耳机/音箱
- **网络**: 2.4GHz WiFi (5GHz不支持)

## 快速开始

### 1. 服务器端

```bash
# 安装依赖
cd server
pip install -r requirements.txt

# 配置API Key (修改app.py中的DASHSCOPE_API_KEY)
# 获取地址: https://dashscope.console.aliyun.com/

# 运行服务器
python app.py
```

### 2. K230端

1. 修改 `src/main_voice.py` 中的配置：
```python
WIFI_SSID = "你的WiFi名称"      # 仅支持2.4GHz
WIFI_PASSWORD = "WiFi密码"
SERVER_IP = "服务器IP地址"       # 运行app.py的电脑IP
```

2. 将 `src/` 目录内容复制到K230的 `/sdcard/pet/`

3. 运行：
```python
exec(open('/sdcard/pet/main_voice.py').read())
```

4. 按下按钮开始说话，松开等待回复

## 项目结构

```
k230_Claude/
├── src/                      # K230端代码
│   ├── main_voice.py         # 语音版主程序 ★
│   ├── main.py               # 视觉版主程序
│   ├── display/              # 显示模块
│   │   └── pet_face.py       # 表情渲染
│   ├── vision/               # 视觉模块
│   │   └── head_pose.py      # 头部检测
│   └── network/              # 网络测试
│       ├── test_wifi.py
│       ├── test_audio.py
│       └── ...
├── server/                   # PC服务器
│   ├── app.py                # 主服务器(ASR+LLM+TTS)
│   ├── test_server.py        # 测试服务器
│   └── requirements.txt
├── docs/                     # 文档
│   ├── architecture.md       # 架构设计
│   └── development_plan.md   # 开发计划
└── CLAUDE.md                 # Claude Code指南
```

## 版本历史

### v0.1.0 - 语音对话版 (2026-01-02)
- 实现完整语音对话流程
- K230录音 → 服务器ASR → LLM对话 → TTS合成 → K230播放
- 表情动画（眨眼、呼吸、说话）
- 解决Display与Audio共用MediaManager的冲突

## 开发笔记

### K230 MicroPython注意事项

1. **无urequests模块** - 需用原生socket实现HTTP
2. **无f-string多行支持** - 使用字符串拼接
3. **WiFi仅2.4GHz** - iPhone热点需开启"最大兼容性"
4. **音频仅WAV格式** - 不支持MP3
5. **Display与Audio冲突** - 不能同时使用，需切换

### 关键经验

1. **MediaManager不要频繁init/deinit** - 会导致网络中断
2. **HTTP大数据分块发送** - 170KB音频需分块
3. **服务器响应需等待** - ASR+LLM+TTS约5-10秒
4. **Display.init()必须在MediaManager.init()之前**

## 依赖

### 服务器端
- Flask >= 2.0.0
- openai >= 1.0.0 (用于调用通义千问)
- edge-tts >= 6.1.0
- dashscope >= 1.10.0

### K230端
- CanMV K230固件 v1.4+
- 3.1寸LCD扩展板

## 许可证

MIT License

## 致谢

- [嘉楠科技](https://www.canaan-creative.com/) - K230芯片
- [立创开发板](https://www.lckfb.com/) - 庐山派开发板
- [阿里云](https://dashscope.console.aliyun.com/) - 通义千问API
- [Edge-TTS](https://github.com/rany2/edge-tts) - 免费TTS
