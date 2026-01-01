"""
K230 图片采集+上传测试
部署到 /sdcard/pet/network/test_image_upload.py
"""

import time
import gc
import json
import socket

try:
    import ubinascii
except ImportError:
    import binascii as ubinascii

from network import WLAN
from media.sensor import *
from media.display import *
from media.media import *

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


def init_camera():
    """初始化摄像头"""
    print("初始化摄像头...")

    sensor = Sensor()
    sensor.reset()

    # 使用较小分辨率
    sensor.set_framesize(width=640, height=480, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    MediaManager.init()
    sensor.run()

    print("摄像头就绪")
    return sensor


def capture_and_compress(sensor, quality=70):
    """采集图片并压缩"""
    img = sensor.snapshot(chn=CAM_CHN_ID_0)

    # JPEG压缩
    compressed = img.compress(quality=quality)

    return compressed


def upload_image(img_data):
    """上传图片到服务器"""
    # Base64编码
    b64_data = ubinascii.b2a_base64(img_data).decode().strip()

    print("图片大小: " + str(len(img_data)) + " bytes")
    print("Base64大小: " + str(len(b64_data)) + " bytes")

    # 构建请求
    payload = {
        "image": b64_data,
        "timestamp": time.time()
    }

    # 发送
    print("上传中...")
    start = time.ticks_ms()

    status, resp = http_post_json(SERVER_IP, SERVER_PORT, "/upload/image", payload)

    elapsed = time.ticks_diff(time.ticks_ms(), start)
    print("上传耗时: " + str(elapsed) + "ms")
    print("状态码: " + str(status))
    print("响应: " + resp)

    return status == 200


def cleanup(sensor):
    """清理资源"""
    print("清理资源...")
    sensor.stop()
    MediaManager.deinit()


if __name__ == "__main__":
    print("=" * 40)
    print("K230 图片上传测试")
    print("=" * 40)

    sensor = None
    try:
        # 连接WiFi
        connect_wifi()

        # 初始化摄像头
        sensor = init_camera()

        # 等待摄像头稳定
        print("等待摄像头稳定...")
        time.sleep(2)

        # 拍照测试
        print("\n--- 拍照并上传 ---")
        gc.collect()

        # 采集压缩
        img_data = capture_and_compress(sensor, quality=70)

        # 上传
        success = upload_image(img_data)

        # 释放内存
        del img_data
        gc.collect()

        print("\n" + "=" * 40)
        if success:
            print("图片上传成功!")
            print("请检查服务器端 uploads 目录")
        else:
            print("图片上传失败")
        print("=" * 40)

    except Exception as e:
        print("错误: " + str(e))
        import sys
        sys.print_exception(e)
    finally:
        if sensor:
            cleanup(sensor)
