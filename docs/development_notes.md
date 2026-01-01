# K230 桌面宠物开发笔记

## 关键经验总结

本文档记录了在K230开发板上实现语音交互桌面宠物过程中的关键经验和踩坑记录。

---

## 1. 架构设计

### 1.1 为什么采用"边缘设备 + 网关"架构

K230的MicroPython环境有以下限制：
- **不支持TLS/HTTPS** - 无法直接调用云端API（如通义千问、Azure等）
- **不支持WSS** - WebSocket Secure不可用
- **WiFi仅支持2.4GHz** - 5GHz网络无法连接

因此采用了PC服务器作为网关的架构：

```
K230 (边缘设备)          PC服务器 (网关)           云端API
     │                        │                      │
     │  HTTP (无加密)         │  HTTPS               │
     │ ─────────────────────> │ ──────────────────> │
     │    录音WAV             │    语音识别(ASR)      │
     │ <───────────────────── │ <────────────────── │
     │    回复WAV             │    大模型对话(LLM)    │
     │                        │    语音合成(TTS)      │
```

### 1.2 HTTP vs WebSocket

最终选择HTTP而非WebSocket：
- K230的socket实现简单可靠
- 语音对话是"请求-响应"模式，HTTP天然适合
- 避免了长连接维护的复杂性

---

## 2. K230 MicroPython 特殊性

### 2.1 没有urequests模块

K230的MicroPython**没有**`urequests`模块，必须用原生socket实现HTTP：

```python
import socket

def http_post_json(host, port, path, data):
    s = socket.socket()
    s.connect((host, port))

    body = json.dumps(data)
    request = "POST {} HTTP/1.1\r\n".format(path)
    request += "Host: {}:{}\r\n".format(host, port)
    request += "Content-Type: application/json\r\n"
    request += "Content-Length: {}\r\n".format(len(body))
    request += "Connection: close\r\n\r\n"

    s.send(request.encode())
    s.send(body.encode())

    # 读取响应...
```

### 2.2 大数据HTTP上传必须分块

170KB的音频数据一次性send会失败，必须分块发送：

```python
body_bytes = body.encode()
sent = 0
chunk_size = 4096  # 4KB分块

while sent < len(body_bytes):
    end = min(sent + chunk_size, len(body_bytes))
    n = s.send(body_bytes[sent:end])
    sent += n
    print("已发送: {}/{}".format(sent, len(body_bytes)))
```

### 2.3 不支持f-string多行

```python
# 错误 - K230不支持
f"""POST {path} HTTP/1.1
Host: {host}"""

# 正确 - 使用字符串拼接
"POST " + path + " HTTP/1.1\r\n" + "Host: " + host
```

---

## 3. MediaManager 与 Display/Audio 冲突

### 3.1 核心问题

K230的`Display`和`PyAudio`模块共用`MediaManager`，但它们不能同时工作。

### 3.2 错误的做法

```python
# 错误！这会导致WiFi断开
MediaManager.deinit()  # 这会破坏网络连接
```

### 3.3 正确的做法

```python
# 正确！只deinit Display，保留MediaManager
Display.deinit()
time.sleep_ms(500)

# 执行音频操作...
record_audio()
play_audio()

# 恢复显示
Display.init(Display.ST7701, width=800, height=480, to_ide=True)
```

### 3.4 初始化顺序

```python
# 首次初始化的正确顺序：
Display.init(Display.ST7701, width=800, height=480, to_ide=True)
MediaManager.init()  # Display.init()必须在前
```

---

## 4. 音频录制与播放

### 4.1 录音实现

```python
from media.pyaudio import PyAudio

def record_audio(seconds):
    p = PyAudio()
    p.initialize(CHUNK)
    MediaManager.init()

    stream = p.open(
        format=paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=CHUNK
    )

    frames = []
    for i in range(int(16000 / CHUNK * seconds)):
        data = stream.read()
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    MediaManager.deinit()

    # 保存为WAV文件...
```

### 4.2 播放实现

```python
def play_audio(filename):
    p = PyAudio()
    p.initialize(CHUNK)
    MediaManager.init()

    with open(filename, 'rb') as f:
        f.read(44)  # 跳过WAV头
        stream = p.open(
            format=paInt16,
            channels=1,
            rate=16000,
            output=True,
            frames_per_buffer=CHUNK
        )

        while True:
            data = f.read(CHUNK * 2)
            if not data:
                break
            stream.write(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    MediaManager.deinit()
```

### 4.3 音频格式要求

- **仅支持WAV格式** - 不支持MP3/AAC
- **采样率**: 16000Hz（ASR要求）或其他标准值
- **位深**: 16bit
- **声道**: 单声道

---

## 5. 网络通信

### 5.1 WiFi连接

```python
from network import WLAN

def connect_wifi(ssid, password):
    wlan = WLAN(0)  # 0=STA模式
    wlan.connect(ssid, password)

    for _ in range(100):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("已连接, IP:", ip)
            return True
        time.sleep_ms(100)

    return False
```

注意事项：
- **仅支持2.4GHz** - iPhone热点需开启"最大兼容性"
- 连接后获取的IP用于服务器端调试

### 5.2 HTTP响应等待

服务器处理ASR+LLM+TTS需要5-10秒，必须等待：

```python
# 发送请求后
s.send(body_bytes)

# 关键！等待服务器处理
time.sleep(5)

# 然后再读取响应
response = b""
while True:
    try:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
    except:
        break
```

---

## 6. 服务器端实现

### 6.1 技术栈

- **Flask** - Web框架
- **DashScope** - 阿里云Paraformer ASR
- **OpenAI兼容API** - 通义千问LLM
- **Edge-TTS** - 免费语音合成
- **FFmpeg** - MP3转WAV（K230兼容格式）

### 6.2 关键配置

```python
# TTS输出必须是WAV格式
subprocess.run([
    'ffmpeg', '-y', '-i', mp3_file,
    '-ar', '16000',      # 采样率
    '-ac', '1',          # 单声道
    '-sample_fmt', 's16', # 16bit
    output_file
])
```

---

## 7. 调试技巧

### 7.1 串口输出

```python
print("[状态] 正在录音...")
print("[发送] {} 字节".format(len(data)))
print("[响应] {}".format(response[:100]))
```

### 7.2 分步测试

1. 先测WiFi连接
2. 再测HTTP GET（ping）
3. 再测小数据POST
4. 再测大文件上传
5. 最后整合测试

### 7.3 常见问题排查

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| WiFi连不上 | 5GHz网络 | 使用2.4GHz |
| HTTP响应空 | 调用了MediaManager.deinit() | 只deinit Display |
| 录音卡住 | Display未关闭 | 先Display.deinit() |
| 播放无声 | WAV格式不对 | 检查采样率/位深 |

---

## 8. 性能数据

| 操作 | 耗时 |
|------|------|
| 录音4秒 | ~4秒 |
| HTTP上传170KB | ~1秒 |
| 服务器处理(ASR+LLM+TTS) | 5-8秒 |
| HTTP下载音频 | ~1秒 |
| 播放回复 | 2-4秒 |
| **总计一轮对话** | **~15秒** |

---

## 9. 待优化项

1. **流式TTS** - 边合成边播放，减少等待时间
2. **VAD检测** - 自动检测语音结束，无需固定录音时长
3. **本地唤醒词** - 避免一直按键
4. **表情联动** - 说话时嘴巴动画

---

## 10. 参考资源

- [CanMV K230 文档](https://developer.canaan-creative.com/k230_canmv)
- [庐山派开发板资料](https://www.lckfb.com)
- [通义千问API](https://dashscope.console.aliyun.com/)
- [Edge-TTS](https://github.com/rany2/edge-tts)
