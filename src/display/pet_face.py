# 桌宠表情显示模块 - 使用image内置绘制函数

import time
import math
import image
from media.display import *
from media.media import *
import urandom

class PetFace:
    """桌宠表情 - 使用image库内置绘制（C实现，高性能）"""

    def __init__(self, width=800, height=480):
        self.width = width
        self.height = height
        self.img = image.Image(width, height, image.ARGB8888)

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

        # 瞳孔位置（平滑移动）
        self.pupil_x = 0.0
        self.pupil_y = 0.0
        self.pupil_target_x = 0.0
        self.pupil_target_y = 0.0
        self.pupil_move_range = 22
        self.pupil_smooth = 0.2

        # 嘴巴
        self.mouth_y = self.face_y + 90

        # 表情
        self.expression = "neutral"

        # 颜色 (ARGB8888格式) - 背景透明
        self.color_bg = (0, 0, 0, 0)  # 透明背景
        self.color_white = (255, 255, 255, 255)
        self.color_pupil = (50, 50, 60, 255)
        self.color_mouth = (255, 120, 120, 255)
        self.color_blush = (255, 180, 180, 255)

        # 眨眼
        self.blink_state = 0.0
        self.blink_closing = False
        self.next_blink = 0
        self._schedule_blink()

        # 呼吸
        self.breath_phase = 0.0

        # 说话
        self.talk_phase = 0.0

    def _schedule_blink(self):
        self.next_blink = time.ticks_ms() + urandom.randint(2500, 5000)

    def set_eye_target(self, tx, ty):
        self.pupil_target_x = max(-1, min(1, tx)) * self.pupil_move_range
        self.pupil_target_y = max(-1, min(1, ty)) * self.pupil_move_range

    def look_at_face(self, fx, fy, fw, fh):
        tx = -((fx / fw) * 2 - 1) * 0.8
        ty = ((fy / fh) * 2 - 1) * 0.6
        self.set_eye_target(tx, ty)

    def set_expression(self, expr):
        self.expression = expr

    def _draw_filled_circle(self, cx, cy, r, color):
        """用同心圆模拟填充"""
        if r <= 0:
            return
        cx, cy, r = int(cx), int(cy), int(r)
        # 从外到内画同心圆
        for radius in range(r, 0, -1):
            self.img.draw_circle(cx, cy, radius, color=color, thickness=2)
        # 中心点
        self.img.draw_circle(cx, cy, 1, color=color, thickness=1)

    def _draw_filled_ellipse(self, cx, cy, rx, ry, color):
        """用同心椭圆模拟填充"""
        if rx <= 0 or ry <= 0:
            return
        cx, cy = int(cx), int(cy)
        rx, ry = int(rx), int(ry)
        # 从外到内画同心椭圆
        steps = max(rx, ry)
        for i in range(steps, 0, -1):
            scale = i / steps
            self.img.draw_ellipse(cx, cy, int(rx * scale), int(ry * scale),
                                  0, 0, 360, color=color, thickness=2)

    def _draw_filled_rect(self, x, y, w, h, color):
        """填充矩形"""
        self.img.draw_rectangle(int(x), int(y), int(w), int(h),
                                color=color, thickness=-1, fill=True)

    def _update(self):
        """更新动画状态"""
        # 瞳孔平滑移动
        self.pupil_x += (self.pupil_target_x - self.pupil_x) * self.pupil_smooth
        self.pupil_y += (self.pupil_target_y - self.pupil_y) * self.pupil_smooth

        # 眨眼
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

        # 呼吸
        self.breath_phase += 0.1
        if self.breath_phase > 6.28:
            self.breath_phase -= 6.28

        # 说话
        if self.expression == "talking":
            self.talk_phase += 0.5

    def _draw_eye(self, cx, cy):
        """绘制眼睛"""
        breath = int(math.sin(self.breath_phase) * 3)
        cy = cy + breath

        # 眨眼压扁
        squash = 1.0 - self.blink_state * 0.85
        ry = int(self.eye_radius * squash)

        if self.expression == "happy":
            ry = int(self.eye_radius * 0.35)
            self._draw_filled_ellipse(cx, cy, self.eye_radius, ry, self.color_white)
        elif self.expression == "sleepy":
            ry = int(self.eye_radius * 0.45 * squash)
            self._draw_filled_ellipse(cx, cy, self.eye_radius, max(3, ry), self.color_white)
            if ry > 8:
                px = int(cx + self.pupil_x * 0.3)
                self._draw_filled_circle(px, cy + 5, self.pupil_radius - 8, self.color_pupil)
        elif self.expression == "curious":
            er = self.eye_radius + 10
            ry = int(er * squash)
            self._draw_filled_ellipse(cx, cy, er, max(3, ry), self.color_white)
            if ry > 15:
                px = int(cx + self.pupil_x)
                py = int(cy + self.pupil_y)
                pr = self.pupil_radius + 5
                pry = int(pr * squash)
                self._draw_filled_ellipse(px, py, pr, max(3, pry), self.color_pupil)
                self._draw_filled_circle(px - 8, py - 8, 8, self.color_white)
        else:
            # neutral / talking
            self._draw_filled_ellipse(cx, cy, self.eye_radius, max(3, ry), self.color_white)
            if ry > 12:
                px = int(cx + self.pupil_x)
                py = int(cy + self.pupil_y)
                pry = int(self.pupil_radius * squash)
                self._draw_filled_ellipse(px, py, self.pupil_radius, max(3, pry), self.color_pupil)
                self._draw_filled_circle(px - 6, py - 6, 6, self.color_white)

    def _draw_mouth(self):
        """绘制嘴巴"""
        breath = int(math.sin(self.breath_phase) * 2)
        my = self.mouth_y + breath
        mx = self.face_x

        if self.expression == "happy":
            # 微笑弧线
            for i in range(-30, 31, 10):
                y_off = int((i * i) / 45)
                self._draw_filled_circle(mx + i, my + y_off, 4, self.color_mouth)
        elif self.expression == "curious":
            # 画圆环（用同心圆，不填充中心）
            for radius in range(16, 9, -1):
                self.img.draw_circle(mx, my, radius, color=self.color_mouth, thickness=2)
        elif self.expression == "talking":
            # 说话椭圆
            mo = int(12 + 14 * abs(math.sin(self.talk_phase)))
            self._draw_filled_ellipse(mx, my, 22, mo, self.color_mouth)
        else:
            # neutral / sleepy - 横线
            self._draw_filled_rect(mx - 25, my - 2, 50, 5, self.color_mouth)

    def _draw_blush(self):
        """绘制腮红"""
        if self.expression == "happy":
            breath = int(math.sin(self.breath_phase) * 2)
            by = self.face_y + 40 + breath
            lx = self.left_eye_x - 35
            rx = self.right_eye_x + 35
            self._draw_filled_ellipse(lx, by, 20, 12, self.color_blush)
            self._draw_filled_ellipse(rx, by, 20, 12, self.color_blush)

    def render(self):
        """渲染一帧"""
        self._update()

        # 清空画面（透明背景）
        self.img.clear()

        # 绘制元素
        self._draw_blush()
        self._draw_eye(self.left_eye_x, self.eye_y)
        self._draw_eye(self.right_eye_x, self.eye_y)
        self._draw_mouth()

        return self.img


# ==================== 测试 ====================
if __name__ == "__main__":
    import os
    import gc
    import sys

    print("=" * 50)
    print("桌宠动画测试 (image内置函数版)")
    print("=" * 50)

    try:
        Display.init(Display.ST7701, width=800, height=480, to_ide=True)
        MediaManager.init()

        pet = PetFace(800, 480)

        expressions = ["neutral", "happy", "curious", "sleepy", "talking"]
        expr_idx = 0
        frame = 0

        print("使用image库C函数绘制")
        print("每5秒切换表情")

        fps_time = time.ticks_ms()
        fps_count = 0

        while True:
            os.exitpoint()

            if frame % 150 == 0:
                pet.set_expression(expressions[expr_idx])
                print(f"表情: {expressions[expr_idx]}")
                expr_idx = (expr_idx + 1) % len(expressions)

            # 眼睛8字运动
            t = time.ticks_ms() / 1500.0
            pet.set_eye_target(math.sin(t) * 0.7, math.sin(t * 2) * 0.4)

            img = pet.render()
            Display.show_image(img)

            frame += 1
            fps_count += 1

            # 每秒显示帧率
            if time.ticks_ms() - fps_time > 1000:
                print(f"FPS: {fps_count}")
                fps_count = 0
                fps_time = time.ticks_ms()

            gc.collect()

    except KeyboardInterrupt:
        print("退出")
    except BaseException as e:
        print(f"异常: {e}")
    finally:
        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        MediaManager.deinit()
