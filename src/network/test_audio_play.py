"""
K230 音频下载+播放测试
部署到 /sdcard/pet/network/test_audio_play.py

测试前：
1. 插入3.5mm耳机或音箱
2. 确保服务器已运行
"""

import os
import time
import gc
import json
import socket

from network import WLAN
from media.media import *
from media.pyaudio import *
import media.wave as wave

# ============ 配置 ============
WIFI_SSID = "WQ's iPhone"
WIFI_PASSWORD = "12345678"
SERVER_IP = "172.20.10.3"
SERVER_PORT = 8080
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


def http_get(host, port, path):
    """发送HTTP GET请求，返回响应体"""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.connect(addr)

    request = "GET " + path + " HTTP/1.1\r\n"
    request += "Host: " + host + "\r\n"
    request += "Connection: close\r\n\r\n"
    s.send(request.encode())

    response = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
    s.close()

    # 分离header和body
    parts = response.split(b"\r\n\r\n", 1)
    header = parts[0].decode()
    body = parts[1] if len(parts) > 1 else b""

    # 获取状态码
    status_line = header.split("\r\n")[0]
    status_code = int(status_line.split()[1])

    return status_code, body


def http_get_json(host, port, path):
    """GET请求返回JSON"""
    status, body = http_get(host, port, path)
    return status, json.loads(body.decode())


def download_audio(audio_url):
    """下载音频文件"""
    print("下载音频: " + audio_url)
    start = time.ticks_ms()

    status, data = http_get(SERVER_IP, SERVER_PORT, audio_url)

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("下载耗时: " + str(elapsed) + "ms")
    print("文件大小: " + str(len(data)) + " bytes")

    if status != 200:
        raise Exception("下载失败: " + str(status))

    # 保存到本地
    local_file = "/sdcard/download_audio.wav"
    with open(local_file, 'wb') as f:
        f.write(data)

    print("保存到: " + local_file)
    return local_file


def play_audio(filename):
    """播放WAV音频文件"""
    print("播放音频: " + filename)

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

    print("采样率: " + str(wf.get_framerate()))
    print("声道数: " + str(wf.get_channels()))
    print("播放中...")

    data = wf.read_frames(CHUNK)
    while data:
        stream.write(data)
        data = wf.read_frames(CHUNK)

    print("播放完成!")

    stream.stop_stream()
    stream.close()
    p.terminate()
    wf.close()
    MediaManager.deinit()


if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    print("=" * 40)
    print("K230 音频下载+播放测试")
    print("=" * 40)
    print("请确保已插入3.5mm耳机或音箱")
    print()

    try:
        # 连接WiFi
        connect_wifi()

        # 1. 请求服务器生成测试音频
        print("\n--- 请求测试音频 ---")
        status, resp = http_get_json(SERVER_IP, SERVER_PORT, "/test_audio")
        print("服务器响应: " + str(resp))

        if status != 200 or resp.get("status") != "ok":
            raise Exception("获取测试音频失败")

        audio_url = resp.get("audio_url")

        # 2. 下载音频
        print("\n--- 下载音频 ---")
        local_file = download_audio(audio_url)

        # 3. 播放音频
        print("\n--- 播放音频 ---")
        play_audio(local_file)

        gc.collect()

        print("\n" + "=" * 40)
        print("音频播放测试完成!")
        print("如果听到440Hz的嘟声(约1秒)，说明成功")
        print("=" * 40)

    except Exception as e:
        print("错误: " + str(e))
        import sys
        sys.print_exception(e)
