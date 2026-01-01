"""
K230 完整语音对话测试
录音 -> 服务器(ASR+LLM+TTS) -> 播放回复

部署到 /sdcard/pet/network/test_voice_chat.py
"""

import os
import time
import gc
import json
import socket

try:
    import ubinascii
except ImportError:
    import binascii as ubinascii

from network import WLAN
from media.media import *
from media.pyaudio import *
import media.wave as wave

# ============ 配置 ============
WIFI_SSID = "WQ's iPhone"
WIFI_PASSWORD = "12345678"
SERVER_IP = "172.20.10.3"
SERVER_PORT = 8080

RECORD_SECONDS = 3
SAMPLE_RATE = 16000
# ==============================


def connect_wifi():
    """连接WiFi"""
    wlan = WLAN(0)
    if wlan.isconnected():
        print("WiFi已连接: " + wlan.ifconfig()[0])
        return wlan

    print("连接WiFi: " + WIFI_SSID)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > 15:
            raise Exception("WiFi连接超时")
        time.sleep(0.5)

    print("已连接: " + wlan.ifconfig()[0])
    return wlan


def http_post_json(host, port, path, data):
    """发送HTTP POST JSON请求"""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(30)
    s.connect(addr)

    body = json.dumps(data)
    request = "POST " + path + " HTTP/1.1\r\n"
    request += "Host: " + host + "\r\n"
    request += "Content-Type: application/json\r\n"
    request += "Content-Length: " + str(len(body)) + "\r\n"
    request += "Connection: close\r\n"
    request += "\r\n"
    request += body
    s.send(request.encode())

    response = b""
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            response += chunk
        except:
            break
    s.close()

    parts = response.split(b"\r\n\r\n", 1)
    header = parts[0].decode()
    resp_body = parts[1].decode() if len(parts) > 1 else ""
    status_line = header.split("\r\n")[0]
    status_code = int(status_line.split()[1])

    return status_code, resp_body


def http_get_binary(host, port, path):
    """GET请求返回二进制数据"""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(30)
    s.connect(addr)

    request = "GET " + path + " HTTP/1.1\r\n"
    request += "Host: " + host + "\r\n"
    request += "Connection: close\r\n\r\n"
    s.send(request.encode())

    response = b""
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            response += chunk
        except:
            break
    s.close()

    parts = response.split(b"\r\n\r\n", 1)
    body = parts[1] if len(parts) > 1 else b""
    return body


def record_audio(duration):
    """录制音频，返回WAV字节数据"""
    print("准备录音 " + str(duration) + " 秒...")
    print("3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print(">>> 开始说话!")

    CHUNK = int(SAMPLE_RATE / 25)
    FORMAT = paInt16
    CHANNELS = 1

    p = PyAudio()
    p.initialize(CHUNK)
    MediaManager.init()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    frames = []
    total_chunks = int(SAMPLE_RATE / CHUNK * duration)

    for i in range(total_chunks):
        data = stream.read()
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    MediaManager.deinit()

    print("录音完成!")

    # 保存到临时文件
    temp_file = "/sdcard/temp_record.wav"
    wf = wave.open(temp_file, 'wb')
    wf.set_channels(CHANNELS)
    wf.set_sampwidth(2)  # 16-bit = 2 bytes
    wf.set_framerate(SAMPLE_RATE)
    wf.write_frames(b''.join(frames))
    wf.close()

    # 读取文件内容
    with open(temp_file, 'rb') as f:
        wav_data = f.read()

    return wav_data


def play_audio(filename):
    """播放WAV音频"""
    print("播放回复...")

    wf = wave.open(filename, 'rb')
    CHUNK = int(wf.get_framerate() / 25)

    p = PyAudio()
    p.initialize(CHUNK)
    MediaManager.init()

    stream = p.open(
        format=p.get_format_from_width(wf.get_sampwidth()),
        channels=wf.get_channels(),
        rate=wf.get_framerate(),
        output=True,
        frames_per_buffer=CHUNK
    )

    data = wf.read_frames(CHUNK)
    while data:
        stream.write(data)
        data = wf.read_frames(CHUNK)

    stream.stop_stream()
    stream.close()
    p.terminate()
    wf.close()
    MediaManager.deinit()

    print("播放完成!")


def voice_chat(audio_data):
    """发送语音到服务器，获取回复"""
    b64_data = ubinascii.b2a_base64(audio_data).decode().strip()

    print("发送到服务器...")
    start = time.ticks_ms()

    status, resp = http_post_json(
        SERVER_IP, SERVER_PORT, "/chat/audio",
        {"audio": b64_data}
    )

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("服务器响应: " + str(elapsed) + "ms")

    if status != 200:
        raise Exception("请求失败: " + str(status))

    result = json.loads(resp)
    if result.get("status") != "ok":
        raise Exception("服务器错误: " + result.get("message", ""))

    print("你说: " + result.get("user_text", ""))
    print("小豆: " + result.get("text", ""))

    return result.get("audio_url")


def download_audio(audio_url):
    """下载音频文件"""
    print("下载回复音频...")
    start = time.ticks_ms()

    data = http_get_binary(SERVER_IP, SERVER_PORT, audio_url)

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("下载: " + str(len(data)) + " bytes, " + str(elapsed) + "ms")

    local_file = "/sdcard/reply.wav"
    with open(local_file, 'wb') as f:
        f.write(data)

    return local_file


if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    print("=" * 40)
    print("K230 语音对话测试")
    print("=" * 40)
    print("请确保:")
    print("1. 已连接麦克风")
    print("2. 已插入耳机/音箱")
    print("3. 服务器正在运行")
    print()

    try:
        # 连接WiFi
        connect_wifi()

        while True:
            print("\n--- 按任意键开始对话 (Ctrl+C退出) ---")
            input()

            # 1. 录音
            audio_data = record_audio(RECORD_SECONDS)
            print("录音大小: " + str(len(audio_data)) + " bytes")

            # 2. 发送到服务器
            audio_url = voice_chat(audio_data)

            # 释放录音数据
            del audio_data
            gc.collect()

            # 3. 下载回复
            local_file = download_audio(audio_url)

            # 4. 播放回复
            play_audio(local_file)

            gc.collect()

    except KeyboardInterrupt:
        print("\n退出")
    except Exception as e:
        print("错误: " + str(e))
        import sys
        sys.print_exception(e)
