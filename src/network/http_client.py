"""
K230 HTTP 客户端封装
部署到 /sdcard/pet/network/http_client.py
"""

import time
import gc

try:
    import urequests
except ImportError:
    print("错误: 找不到 urequests 模块")
    raise

try:
    import ubinascii
except ImportError:
    import binascii as ubinascii

from network import WLAN


class HTTPClient:
    """HTTP客户端封装"""

    def __init__(self, server_url, wifi_ssid=None, wifi_password=None):
        self.server_url = server_url
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.wlan = None

    def connect_wifi(self, timeout=15):
        """连接WiFi"""
        if not self.wifi_ssid:
            raise ValueError("未设置WiFi SSID")

        self.wlan = WLAN(0)

        if self.wlan.isconnected():
            print(f"WiFi已连接: {self.wlan.ifconfig()[0]}")
            return True

        print(f"连接WiFi: {self.wifi_ssid}")
        self.wlan.connect(self.wifi_ssid, self.wifi_password)

        start = time.time()
        while not self.wlan.isconnected():
            if time.time() - start > timeout:
                raise Exception("WiFi连接超时")
            time.sleep(0.5)

        print(f"已连接: {self.wlan.ifconfig()[0]}")
        return True

    def is_connected(self):
        """检查WiFi连接状态"""
        return self.wlan and self.wlan.isconnected()

    def get(self, endpoint):
        """发送GET请求"""
        url = f"{self.server_url}{endpoint}"
        response = urequests.get(url)
        result = {
            "status": response.status_code,
            "text": response.text
        }
        response.close()
        return result

    def post_json(self, endpoint, data):
        """发送POST JSON请求"""
        url = f"{self.server_url}{endpoint}"
        response = urequests.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"}
        )
        result = {
            "status": response.status_code,
            "text": response.text
        }
        response.close()
        return result

    def upload_image(self, image_bytes):
        """上传图片"""
        b64_data = ubinascii.b2a_base64(image_bytes).decode().strip()
        return self.post_json("/upload/image", {
            "image": b64_data,
            "timestamp": time.time()
        })

    def upload_audio(self, audio_bytes, sample_rate=16000):
        """上传音频"""
        b64_data = ubinascii.b2a_base64(audio_bytes).decode().strip()
        return self.post_json("/upload/audio", {
            "audio": b64_data,
            "sample_rate": sample_rate,
            "timestamp": time.time()
        })

    def chat(self, image_bytes=None, audio_bytes=None, local_detect=None):
        """
        发送对话请求
        image_bytes: JPEG图片数据
        audio_bytes: WAV音频数据
        local_detect: 本地检测结果 (dict)
        """
        payload = {
            "timestamp": time.time()
        }

        if image_bytes:
            payload["image"] = ubinascii.b2a_base64(image_bytes).decode().strip()

        if audio_bytes:
            payload["audio"] = ubinascii.b2a_base64(audio_bytes).decode().strip()

        if local_detect:
            payload["local_detect"] = local_detect

        return self.post_json("/chat", payload)

    def download_audio(self, audio_url):
        """
        下载音频文件
        返回原始字节数据
        """
        if audio_url.startswith("/"):
            url = f"{self.server_url}{audio_url}"
        else:
            url = audio_url

        response = urequests.get(url)
        if response.status_code == 200:
            data = response.content
            response.close()
            return data
        else:
            response.close()
            raise Exception(f"下载失败: {response.status_code}")

    def ping(self):
        """心跳测试"""
        try:
            result = self.get("/ping")
            return result["status"] == 200
        except:
            return False
