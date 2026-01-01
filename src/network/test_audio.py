"""
K230 音频录制+上传测试
部署到 /sdcard/pet/network/test_audio.py
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
        chunk = s.recv(1024)
        if not chunk:
            break
        response += chunk
    s.close()

    parts = response.split(b"\r\n\r\n", 1)
    header = parts[0].decode()
    resp_body = parts[1].decode() if len(parts) > 1 else ""
    status_line = header.split("\r\n")[0]
    status_code = int(status_line.split()[1])

    return status_code, resp_body


def record_audio(duration):
    """录制音频，返回WAV文件的字节数据"""
    print("准备录音 " + str(duration) + " 秒...")
    print("3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print("开始录音!")

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
    wf.set_sampwidth(p.get_sample_size(FORMAT))
    wf.set_framerate(SAMPLE_RATE)
    wf.write_frames(b''.join(frames))
    wf.close()

    # 读取文件内容
    with open(temp_file, 'rb') as f:
        wav_data = f.read()

    print("WAV文件大小: " + str(len(wav_data)) + " bytes")

    return wav_data


def upload_audio(audio_data):
    """上传音频到服务器"""
    b64_data = ubinascii.b2a_base64(audio_data).decode().strip()

    print("Base64大小: " + str(len(b64_data)) + " bytes")

    payload = {
        "audio": b64_data,
        "sample_rate": SAMPLE_RATE,
        "duration": RECORD_SECONDS,
        "timestamp": time.time()
    }

    print("上传中...")
    start = time.ticks_ms()

    status, resp = http_post_json(SERVER_IP, SERVER_PORT, "/upload/audio", payload)

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("上传耗时: " + str(elapsed) + "ms")
    print("状态码: " + str(status))
    print("响应: " + resp)

    return status == 200


if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    print("=" * 40)
    print("K230 音频录制+上传测试")
    print("=" * 40)

    try:
        # 连接WiFi
        connect_wifi()

        # 录音
        audio_data = record_audio(RECORD_SECONDS)

        # 上传
        success = upload_audio(audio_data)

        # 释放内存
        del audio_data
        gc.collect()

        print("\n" + "=" * 40)
        if success:
            print("音频上传成功!")
            print("请检查服务器端 uploads 目录")
        else:
            print("音频上传失败")
        print("=" * 40)

    except Exception as e:
        print("错误: " + str(e))
        import sys
        sys.print_exception(e)
