"""
桌面宠物主程序 - 语音对话版
部署到 /sdcard/pet/main_voice.py

功能:
- 启动时连接WiFi
- 显示桌宠表情动画
- 按下按钮录音 → 上传服务器 → 接收回复 → 播放音频
- 播放时显示说话表情
"""

import os
import gc
import sys
import time
import math
import json
import socket
import image
import urandom

try:
    import ubinascii
except ImportError:
    import binascii as ubinascii

from machine import Pin, FPIOA
from network import WLAN
from media.display import *
from media.media import *
from media.pyaudio import *
import media.wave as wave

# ==================== 配置参数 ====================
# WiFi配置
WIFI_SSID = "WQ's iPhone"
WIFI_PASSWORD = "12345678"

# 服务器配置
SERVER_IP = "172.20.10.3"
SERVER_PORT = 8080

# 显示配置
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# 录音配置
RECORD_SECONDS = 4
SAMPLE_RATE = 16000

# 按钮GPIO (GPIO53, 高电平有效)
BUTTON_PIN = 53


# ==================== 网络函数 ====================
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
    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
        s = socket.socket()
        s.settimeout(90)
        print("连接服务器 " + host + ":" + str(port) + "...")
        s.connect(addr)
        print("已连接")

        body = json.dumps(data)
        print("请求体大小: " + str(len(body)) + " 字节")

        # 构建HTTP头
        header = "POST " + path + " HTTP/1.1\r\n"
        header += "Host: " + host + "\r\n"
        header += "Content-Type: application/json\r\n"
        header += "Content-Length: " + str(len(body)) + "\r\n"
        header += "Connection: close\r\n"
        header += "\r\n"

        # 分开发送头和体
        s.send(header.encode())
        print("已发送HTTP头")

        # 分块发送body（大数据）
        body_bytes = body.encode()
        sent = 0
        chunk_size = 4096
        while sent < len(body_bytes):
            end = min(sent + chunk_size, len(body_bytes))
            n = s.send(body_bytes[sent:end])
            sent += n
            if sent % 20000 < chunk_size:
                print("已发送 " + str(sent) + "/" + str(len(body_bytes)) + " 字节")
        print("请求体发送完成")

        # 等待服务器处理 (ASR+LLM+TTS需要5-10秒)
        print("等待服务器处理(约5-10秒)...")
        time.sleep(5)

        # 接收响应
        print("开始接收响应...")
        response = b""
        empty_count = 0

        while empty_count < 10:  # 连续10次空读取才退出
            try:
                chunk = s.recv(4096)
                if chunk:
                    response += chunk
                    print("收到 " + str(len(chunk)) + " 字节, 总计 " + str(len(response)))
                    empty_count = 0  # 重置计数
                else:
                    empty_count += 1
                    if empty_count < 10:
                        time.sleep(1)  # 等待更多数据
            except OSError as e:
                print("读取异常: " + str(e))
                break

        s.close()

        print("总共收到 " + str(len(response)) + " 字节")

        if len(response) == 0:
            print("HTTP响应为空")
            return 0, b""

        parts = response.split(b"\r\n\r\n", 1)
        if len(parts) < 1:
            print("HTTP响应格式错误")
            return 0, b""

        header = parts[0].decode()
        resp_body = parts[1] if len(parts) > 1 else b""

        lines = header.split("\r\n")
        if len(lines) == 0:
            return 0, b""

        status_parts = lines[0].split()
        if len(status_parts) < 2:
            return 0, b""

        status_code = int(status_parts[1])
        print("HTTP状态码: " + str(status_code))
        return status_code, resp_body

    except Exception as e:
        print("HTTP请求异常: " + str(e))
        return 0, b""


def http_get(host, port, path):
    """发送HTTP GET请求，返回响应体"""
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


# ==================== 音频函数 ====================
def record_audio(duration):
    """录制音频，返回WAV文件路径"""
    print("录音 " + str(duration) + " 秒...")

    CHUNK = int(SAMPLE_RATE / 25)
    FORMAT = paInt16
    CHANNELS = 1

    p = PyAudio()
    p.initialize(CHUNK)

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

    print("录音完成!")

    # 保存到临时文件
    temp_file = "/sdcard/pet_record.wav"
    wf = wave.open(temp_file, 'wb')
    wf.set_channels(CHANNELS)
    wf.set_sampwidth(2)  # 16bit = 2 bytes
    wf.set_framerate(SAMPLE_RATE)
    wf.write_frames(b''.join(frames))
    wf.close()

    return temp_file


def play_audio(filename):
    """播放WAV音频文件"""
    print("播放: " + filename)

    # 1. 读取文件到内存
    print("加载音频到内存...")
    with open(filename, 'rb') as f:
        f.read(44)  # 跳过44字节WAV头
        audio_data = f.read()
    print("已加载 {} 字节".format(len(audio_data)))

    # 2. 使用更大的CHUNK减少卡顿
    CHUNK = 2048  # 增大缓冲区
    FORMAT = paInt16
    CHANNELS = 1

    p = PyAudio()
    p.initialize(CHUNK)

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,  # 16000
        output=True,
        frames_per_buffer=CHUNK
    )

    # 3. 播放前等待缓冲区准备
    time.sleep_ms(100)

    # 4. 从内存播放，使用绝对时间控制避免累积误差
    chunk_bytes = CHUNK * 2  # 16bit = 2字节
    chunk_duration_ms = int(CHUNK * 1000 / SAMPLE_RATE)  # 128ms

    start_time = time.ticks_ms()
    chunk_count = 0
    offset = 0

    while offset < len(audio_data):
        end = min(offset + chunk_bytes, len(audio_data))
        chunk = audio_data[offset:end]
        # 补零对齐
        if len(chunk) < chunk_bytes:
            chunk = chunk + bytes(chunk_bytes - len(chunk))
        stream.write(chunk)
        chunk_count += 1
        offset = end

        # 用绝对时间控制，避免累积误差
        target_time = start_time + chunk_count * chunk_duration_ms
        now = time.ticks_ms()
        wait_ms = time.ticks_diff(target_time, now) - 5  # 留5ms余量
        if wait_ms > 0:
            time.sleep_ms(wait_ms)

    # 5. 等待播放完成
    time.sleep_ms(200)

    stream.stop_stream()
    stream.close()
    p.terminate()

    print("播放完成!")


# ==================== 高性能桌宠表情类 ====================
class PetFace:
    """桌宠表情 - 使用image库内置绘制（C实现，高性能）"""

    def __init__(self, width=800, height=480):
        self.width = width
        self.height = height

        # 脸部中心
        self.face_x = width // 2
        self.face_y = height // 2

        # 眼睛配置
        self.eye_radius = 55
        self.pupil_radius = 22
        self.eye_spacing = 160
        self.eye_y_offset = -30
        self.left_eye_x = self.face_x - self.eye_spacing // 2
        self.right_eye_x = self.face_x + self.eye_spacing // 2
        self.eye_y = self.face_y + self.eye_y_offset

        # 嘴巴
        self.mouth_y = self.face_y + 90

        # 表情
        self.expression = "neutral"

        # 颜色 (ARGB8888格式)
        self.color_bg = (40, 44, 52, 255)
        self.color_white = (255, 255, 255, 255)
        self.color_pupil = (50, 50, 60, 255)
        self.color_mouth = (255, 120, 120, 255)
        self.color_blush = (255, 180, 180, 255)
        self.color_status = (100, 200, 100, 255)

        # 眨眼动画
        self.blink_state = 0.0
        self.blink_closing = False
        self.next_blink = 0
        self._schedule_blink()

        # 呼吸动画
        self.breath_phase = 0.0

        # 说话动画
        self.talk_phase = 0.0

        # 状态文字
        self.status_text = ""

    def _schedule_blink(self):
        """安排下一次眨眼"""
        self.next_blink = time.ticks_ms() + urandom.randint(2500, 5000)

    def set_expression(self, expr):
        """设置表情"""
        self.expression = expr

    def set_status(self, text):
        """设置状态文字"""
        self.status_text = text

    def _draw_filled_circle(self, img, cx, cy, r, color):
        """用同心圆模拟填充"""
        if r <= 0:
            return
        cx, cy, r = int(cx), int(cy), int(r)
        for radius in range(r, 0, -1):
            img.draw_circle(cx, cy, radius, color=color, thickness=2)
        img.draw_circle(cx, cy, 1, color=color, thickness=1)

    def _draw_filled_ellipse(self, img, cx, cy, rx, ry, color):
        """用同心椭圆模拟填充"""
        if rx <= 0 or ry <= 0:
            return
        cx, cy = int(cx), int(cy)
        rx, ry = int(rx), int(ry)
        steps = max(rx, ry)
        for i in range(steps, 0, -1):
            scale = i / steps
            img.draw_ellipse(cx, cy, int(rx * scale), int(ry * scale),
                             0, 0, 360, color=color, thickness=2)

    def _draw_filled_rect(self, img, x, y, w, h, color):
        """填充矩形"""
        img.draw_rectangle(int(x), int(y), int(w), int(h),
                           color=color, thickness=-1, fill=True)

    def _update(self):
        """更新动画状态"""
        # 眨眼动画
        now = time.ticks_ms()
        if now > self.next_blink and self.blink_state == 0:
            self.blink_closing = True

        if self.blink_closing:
            self.blink_state += 0.3
            if self.blink_state >= 1.0:
                self.blink_state = 1.0
                self.blink_closing = False
        else:
            if self.blink_state > 0:
                self.blink_state -= 0.3
                if self.blink_state <= 0:
                    self.blink_state = 0
                    self._schedule_blink()

        # 呼吸动画
        self.breath_phase += 0.1
        if self.breath_phase > 6.28:
            self.breath_phase -= 6.28

        # 说话动画
        if self.expression == "talking":
            self.talk_phase += 0.5

    def _draw_eye(self, img, cx, cy):
        """绘制眼睛"""
        breath = int(math.sin(self.breath_phase) * 3)
        cy = cy + breath

        # 眨眼压扁
        squash = 1.0 - self.blink_state * 0.85
        ry = int(self.eye_radius * squash)

        if self.expression == "happy":
            ry = int(self.eye_radius * 0.35)
            self._draw_filled_ellipse(img, cx, cy, self.eye_radius, ry, self.color_white)
        elif self.expression == "sleepy":
            ry = int(self.eye_radius * 0.45 * squash)
            self._draw_filled_ellipse(img, cx, cy, self.eye_radius, max(3, ry), self.color_white)
            if ry > 8:
                self._draw_filled_circle(img, cx, cy + 5, self.pupil_radius - 8, self.color_pupil)
        elif self.expression == "listening":
            # 聆听表情 - 大眼睛
            er = self.eye_radius + 15
            ry = int(er * squash)
            self._draw_filled_ellipse(img, cx, cy, er, max(3, ry), self.color_white)
            if ry > 15:
                pr = self.pupil_radius + 5
                pry = int(pr * squash)
                self._draw_filled_ellipse(img, cx, cy, pr, max(3, pry), self.color_pupil)
                self._draw_filled_circle(img, cx - 10, cy - 10, 10, self.color_white)
        elif self.expression == "thinking":
            # 思考表情 - 眼睛看上
            self._draw_filled_ellipse(img, cx, cy, self.eye_radius, max(3, ry), self.color_white)
            if ry > 12:
                py = cy - 10  # 瞳孔向上
                self._draw_filled_ellipse(img, cx, py, self.pupil_radius, max(3, int(self.pupil_radius * squash)), self.color_pupil)
                self._draw_filled_circle(img, cx - 6, py - 6, 6, self.color_white)
        elif self.expression == "talking":
            # 说话表情 - 正常眼睛
            self._draw_filled_ellipse(img, cx, cy, self.eye_radius, max(3, ry), self.color_white)
            if ry > 12:
                pry = int(self.pupil_radius * squash)
                self._draw_filled_ellipse(img, cx, cy, self.pupil_radius, max(3, pry), self.color_pupil)
                self._draw_filled_circle(img, cx - 6, cy - 6, 6, self.color_white)
        else:
            # neutral
            self._draw_filled_ellipse(img, cx, cy, self.eye_radius, max(3, ry), self.color_white)
            if ry > 12:
                pry = int(self.pupil_radius * squash)
                self._draw_filled_ellipse(img, cx, cy, self.pupil_radius, max(3, pry), self.color_pupil)
                self._draw_filled_circle(img, cx - 6, cy - 6, 6, self.color_white)

    def _draw_mouth(self, img):
        """绘制嘴巴"""
        breath = int(math.sin(self.breath_phase) * 2)
        my = self.mouth_y + breath
        mx = self.face_x

        if self.expression == "happy":
            for i in range(-30, 31, 10):
                y_off = int((i * i) / 45)
                self._draw_filled_circle(img, mx + i, my + y_off, 4, self.color_mouth)
        elif self.expression == "listening":
            # 聆听 - 小圆嘴
            for radius in range(12, 5, -1):
                img.draw_circle(mx, my, radius, color=self.color_mouth, thickness=2)
        elif self.expression == "thinking":
            # 思考 - 歪嘴
            for i in range(-20, 21, 8):
                y_off = int(i / 5)
                self._draw_filled_circle(img, mx + i + 15, my + y_off, 3, self.color_mouth)
        elif self.expression == "talking":
            mo = int(12 + 14 * abs(math.sin(self.talk_phase)))
            self._draw_filled_ellipse(img, mx, my, 22, mo, self.color_mouth)
        else:
            self._draw_filled_rect(img, mx - 25, my - 2, 50, 5, self.color_mouth)

    def _draw_blush(self, img):
        """绘制腮红"""
        if self.expression in ["happy", "talking"]:
            breath = int(math.sin(self.breath_phase) * 2)
            by = self.face_y + 40 + breath
            lx = self.left_eye_x - 35
            rx = self.right_eye_x + 35
            self._draw_filled_ellipse(img, lx, by, 20, 12, self.color_blush)
            self._draw_filled_ellipse(img, rx, by, 20, 12, self.color_blush)

    def _draw_status(self, img):
        """绘制状态文字"""
        if self.status_text:
            img.draw_string_advanced(
                self.face_x - 100, self.height - 60,
                32, self.status_text,
                color=self.color_status
            )

    def render(self, img):
        """渲染一帧到指定图像"""
        self._update()

        # 清空并填充背景
        img.clear()
        img.draw_rectangle(0, 0, self.width, self.height,
                           color=self.color_bg, thickness=-1, fill=True)

        # 绘制元素
        self._draw_blush(img)
        self._draw_eye(img, self.left_eye_x, self.eye_y)
        self._draw_eye(img, self.right_eye_x, self.eye_y)
        self._draw_mouth(img)
        self._draw_status(img)


# ==================== 语音对话处理 ====================
def voice_chat(audio_file):
    """发送音频到服务器进行对话，返回回复音频URL"""
    print("发送音频到服务器...")

    # 读取音频文件
    with open(audio_file, 'rb') as f:
        audio_data = f.read()

    # Base64编码
    b64_data = ubinascii.b2a_base64(audio_data).decode().strip()

    # 发送请求
    payload = {"audio": b64_data}
    status, resp_body = http_post_json(SERVER_IP, SERVER_PORT, "/chat/audio", payload)

    if status != 200:
        print("请求失败: " + str(status))
        return None, None

    # 解析响应
    try:
        resp = json.loads(resp_body.decode())
    except:
        print("JSON解析失败")
        return None, None

    if resp.get("status") != "ok":
        print("服务器返回错误: " + str(resp.get("message")))
        return None, None

    user_text = resp.get("user_text", "")
    reply_text = resp.get("text", "")
    audio_url = resp.get("audio_url")

    print("用户: " + user_text)
    print("小豆: " + reply_text)

    return audio_url, reply_text


def download_audio(audio_url):
    """下载音频文件"""
    print("下载音频: " + audio_url)

    data = http_get(SERVER_IP, SERVER_PORT, audio_url)

    if len(data) < 100:
        print("下载失败，数据太小")
        return None

    # 保存到本地
    local_file = "/sdcard/pet_reply.wav"
    with open(local_file, 'wb') as f:
        f.write(data)

    print("保存到: " + local_file + " (" + str(len(data)) + " bytes)")
    return local_file


# ==================== 主程序 ====================
if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)

    print("=" * 50)
    print("桌面宠物 - 语音对话版")
    print("=" * 50)

    # 初始化按钮
    fpioa = FPIOA()
    fpioa.set_function(BUTTON_PIN, FPIOA.GPIO53)
    button = Pin(BUTTON_PIN, Pin.IN, pull=Pin.PULL_DOWN)

    # 创建绘图用的图像对象
    img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)

    # 初始化显示器 (必须在MediaManager.init之前)
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    # 初始化媒体管理器
    MediaManager.init()

    # 创建桌宠
    pet = PetFace(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    pet.set_expression("sleepy")
    pet.set_status("启动中...")

    # 渲染一帧
    pet.render(img)
    Display.show_image(img)

    # 连接WiFi
    try:
        pet.set_status("连接WiFi...")
        pet.render(img)
        Display.show_image(img)

        connect_wifi()

        pet.set_expression("happy")
        pet.set_status("WiFi已连接!")
        pet.render(img)
        Display.show_image(img)
        time.sleep(1)

    except Exception as e:
        print("WiFi连接失败: " + str(e))
        pet.set_expression("sleepy")
        pet.set_status("WiFi失败")
        pet.render(img)
        Display.show_image(img)
        time.sleep(3)
        Display.deinit()
        time.sleep_ms(100)
        MediaManager.deinit()
        sys.exit(1)

    # 主循环
    pet.set_expression("neutral")
    pet.set_status("按按钮说话")

    last_button_state = 0
    debounce_time = 0
    DEBOUNCE_MS = 50

    print("-" * 50)
    print("准备就绪! 按下按钮开始说话")
    print("-" * 50)

    try:
        while True:
            os.exitpoint()

            # 检测按钮
            button_state = button.value()
            current_time = time.ticks_ms()

            if button_state == 1 and last_button_state == 0:
                if current_time - debounce_time > DEBOUNCE_MS:
                    debounce_time = current_time

                    # ===== 语音对话流程 =====
                    print("\n>>> 开始对话")

                    # 1. 显示聆听状态
                    pet.set_expression("listening")
                    pet.set_status("正在聆听...")
                    pet.render(img)
                    Display.show_image(img)
                    time.sleep_ms(500)  # 短暂显示

                    # 关闭显示，进入音频模式
                    # 注意：不调用MediaManager.deinit()，避免影响网络
                    print("关闭显示，进入音频模式...")
                    Display.deinit()
                    time.sleep_ms(500)

                    # 2. 录音
                    audio_file = record_audio(RECORD_SECONDS)

                    # 3. 发送到服务器
                    print("发送到服务器...")
                    audio_url, reply_text = voice_chat(audio_file)

                    # 4. 播放回复
                    if audio_url:
                        local_audio = download_audio(audio_url)
                        if local_audio:
                            play_audio(local_audio)

                    # 5. 恢复显示（等待音频资源释放）
                    print("恢复显示...")
                    gc.collect()  # 强制垃圾回收释放音频资源
                    time.sleep(1)

                    # 重试机制
                    for retry in range(3):
                        try:
                            Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
                            break
                        except Exception as e:
                            print("Display初始化失败({}): {}".format(retry + 1, e))
                            gc.collect()
                            time.sleep(1)
                    else:
                        print("Display初始化失败，继续运行...")

                    # 6. 显示完成状态
                    pet.set_expression("happy")
                    if reply_text:
                        if len(reply_text) > 12:
                            pet.set_status(reply_text[:12] + "...")
                        else:
                            pet.set_status(reply_text)
                    else:
                        pet.set_status("按按钮说话")
                    print(">>> 对话结束\n")

            last_button_state = button_state

            # 渲染动画
            pet.render(img)
            Display.show_image(img)

            time.sleep_ms(33)  # ~30 FPS
            gc.collect()

    except KeyboardInterrupt:
        print("用户中断")
    except Exception as e:
        print("异常: " + str(e))
    finally:
        print("清理资源...")
        try:
            Display.deinit()
        except:
            pass
        time.sleep_ms(100)
        try:
            MediaManager.deinit()
        except:
            pass
        print("完成")
