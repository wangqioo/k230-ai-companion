"""
K230 网络配置
部署到 /sdcard/pet/network/config.py

使用前请修改这里的配置!
"""

# ============ WiFi 配置 ============
WIFI_SSID = "WQ's iPhone"      # 修改为你的WiFi名称
WIFI_PASSWORD = "12345678"  # 修改为你的WiFi密码

# ============ 服务器配置 ============
SERVER_IP = "172.20.10.3"    # 修改为你电脑的IP地址
SERVER_PORT = 8080

# ============ 音频配置 ============
AUDIO_SAMPLE_RATE = 16000      # 采样率 (16kHz足够语音识别)
AUDIO_CHANNELS = 1             # 单声道
AUDIO_BIT_DEPTH = 16           # 16位

# ============ 图像配置 ============
IMAGE_MAX_SIZE = 320           # 上传图片最大边长
IMAGE_QUALITY = 70             # JPEG压缩质量 (1-100)

# ============ 计算属性 ============
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}"
