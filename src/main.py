# 桌面宠物主程序 - 整合头部检测 + 高性能表情显示

from libs.PipeLine import PipeLine, ScopedTiming
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
import os
import gc
import sys
import time
import math
import image
import aidemo
import urandom
import nncase_runtime as nn
import ulab.numpy as np
from media.media import *

# ==================== 配置参数 ====================
# 显示配置
DISPLAY_MODE = "lcd"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
RGB888P_SIZE = [1920, 1080]

# 唤醒配置
WAKE_YAW_THRESHOLD = 20      # yaw角度小于此值时判定为"正对"
EXIT_YAW_THRESHOLD = 35      # yaw角度大于此值时开始计时退出
EXIT_TIMEOUT_FRAMES = 90     # 持续多少帧后退出（约3秒）


# ==================== 高性能桌宠表情类 ====================
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

        # 眨眼动画
        self.blink_state = 0.0
        self.blink_closing = False
        self.next_blink = 0
        self._schedule_blink()

        # 呼吸动画
        self.breath_phase = 0.0

        # 说话动画
        self.talk_phase = 0.0

    def _schedule_blink(self):
        """安排下一次眨眼"""
        self.next_blink = time.ticks_ms() + urandom.randint(2500, 5000)

    def set_eye_target(self, tx, ty):
        """设置眼睛目标位置"""
        self.pupil_target_x = max(-1, min(1, tx)) * self.pupil_move_range
        self.pupil_target_y = max(-1, min(1, ty)) * self.pupil_move_range

    def look_at_face(self, fx, fy, fw, fh):
        """根据人脸位置设置眼睛目标"""
        tx = -((fx / fw) * 2 - 1) * 0.8
        ty = ((fy / fh) * 2 - 1) * 0.6
        self.set_eye_target(tx, ty)

    def set_expression(self, expr):
        """设置表情"""
        self.expression = expr

    def _draw_filled_circle(self, cx, cy, r, color):
        """用同心圆模拟填充 - C函数高性能"""
        if r <= 0:
            return
        cx, cy, r = int(cx), int(cy), int(r)
        for radius in range(r, 0, -1):
            self.img.draw_circle(cx, cy, radius, color=color, thickness=2)
        self.img.draw_circle(cx, cy, 1, color=color, thickness=1)

    def _draw_filled_ellipse(self, cx, cy, rx, ry, color):
        """用同心椭圆模拟填充 - C函数高性能"""
        if rx <= 0 or ry <= 0:
            return
        cx, cy = int(cx), int(cy)
        rx, ry = int(rx), int(ry)
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
            for i in range(-30, 31, 10):
                y_off = int((i * i) / 45)
                self._draw_filled_circle(mx + i, my + y_off, 4, self.color_mouth)
        elif self.expression == "curious":
            # 画圆环（用同心圆，不填充中心）
            for radius in range(16, 9, -1):
                self.img.draw_circle(mx, my, radius, color=self.color_mouth, thickness=2)
        elif self.expression == "talking":
            mo = int(12 + 14 * abs(math.sin(self.talk_phase)))
            self._draw_filled_ellipse(mx, my, 22, mo, self.color_mouth)
        else:
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


# ==================== 人脸检测类 ====================
class FaceDetApp(AIBase):
    def __init__(self, kmodel_path, model_input_size, anchors,
                 confidence_threshold=0.5, nms_threshold=0.2,
                 rgb888p_size=[1920, 1080], display_size=[800, 480], debug_mode=0):
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.anchors = anchors
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.debug_mode = debug_mode
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT, np.uint8, np.uint8)

    def config_preprocess(self, input_image_size=None):
        ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
        self.ai2d.pad(self.get_pad_param(), 0, [104, 117, 123])
        self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
        self.ai2d.build([1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                        [1, 3, self.model_input_size[1], self.model_input_size[0]])

    def postprocess(self, results):
        res = aidemo.face_det_post_process(self.confidence_threshold, self.nms_threshold,
                                            self.model_input_size[0], self.anchors,
                                            self.rgb888p_size, results)
        if len(res) == 0:
            return res
        else:
            return res[0]

    def get_pad_param(self):
        dst_w = self.model_input_size[0]
        dst_h = self.model_input_size[1]
        ratio_w = dst_w / self.rgb888p_size[0]
        ratio_h = dst_h / self.rgb888p_size[1]
        ratio = min(ratio_w, ratio_h)
        new_w = int(ratio * self.rgb888p_size[0])
        new_h = int(ratio * self.rgb888p_size[1])
        dw = (dst_w - new_w) / 2
        dh = (dst_h - new_h) / 2
        return [0, 0, 0, 0, int(round(0)), int(round(dh * 2 + 0.1)),
                int(round(0)), int(round(dw * 2 - 0.1))]


class FacePoseApp(AIBase):
    def __init__(self, kmodel_path, model_input_size,
                 rgb888p_size=[1920, 1080], display_size=[800, 480], debug_mode=0):
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.debug_mode = debug_mode
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT, np.uint8, np.uint8)

    def config_preprocess(self, det, input_image_size=None):
        ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
        matrix_dst = self.get_affine_matrix(det)
        self.ai2d.affine(nn.interp_method.cv2_bilinear, 0, 0, 127, 1, matrix_dst)
        self.ai2d.build([1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                        [1, 3, self.model_input_size[1], self.model_input_size[0]])

    def postprocess(self, results):
        R, euler = self.get_euler(results[0][0])
        return R, euler

    def get_affine_matrix(self, bbox):
        factor = 2.7
        x1, y1, w, h = map(lambda x: int(round(x, 0)), bbox[:4])
        edge_size = self.model_input_size[1]
        trans_distance = edge_size / 2.0
        center_x = x1 + w / 2.0
        center_y = y1 + h / 2.0
        maximum_edge = factor * (h if h > w else w)
        scale = edge_size * 2.0 / maximum_edge
        cx = trans_distance - scale * center_x
        cy = trans_distance - scale * center_y
        return [scale, 0, cx, 0, scale, cy]

    def rotation_matrix_to_euler_angles(self, R):
        sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
        if sy < 1e-6:
            pitch = np.arctan2(-R[1, 2], R[1, 1]) * 180 / np.pi
            yaw = np.arctan2(-R[2, 0], sy) * 180 / np.pi
            roll = 0
        else:
            pitch = np.arctan2(R[2, 1], R[2, 2]) * 180 / np.pi
            yaw = np.arctan2(-R[2, 0], sy) * 180 / np.pi
            roll = np.arctan2(R[1, 0], R[0, 0]) * 180 / np.pi
        return [pitch, yaw, roll]

    def get_euler(self, data):
        R = data[:3, :3].copy()
        euler = self.rotation_matrix_to_euler_angles(R)
        return R, euler


# ==================== 主程序 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("桌面宠物 - 头部朝向唤醒 (高性能版)")
    print("=" * 50)

    # 加载模型
    face_det_kmodel = "/sdcard/examples/kmodel/face_detection_320.kmodel"
    face_pose_kmodel = "/sdcard/examples/kmodel/face_pose.kmodel"
    anchors_path = "/sdcard/examples/utils/prior_data_320.bin"

    anchors = np.fromfile(anchors_path, dtype=np.float)
    anchors = anchors.reshape((4200, 4))

    display_size = [DISPLAY_WIDTH, DISPLAY_HEIGHT]

    # 初始化 PipeLine
    pl = PipeLine(rgb888p_size=RGB888P_SIZE, display_size=display_size, display_mode=DISPLAY_MODE)
    pl.create()

    # 初始化 AI 模型
    face_det = FaceDetApp(face_det_kmodel, model_input_size=[320, 320], anchors=anchors,
                          rgb888p_size=RGB888P_SIZE, display_size=display_size)
    face_pose = FacePoseApp(face_pose_kmodel, model_input_size=[120, 120],
                            rgb888p_size=RGB888P_SIZE, display_size=display_size)
    face_det.config_preprocess()

    # 创建桌宠（高性能版本，带眨眼/呼吸动画）
    pet = PetFace(DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # 状态变量
    state = "IDLE"  # IDLE / ACTIVE
    exit_counter = 0
    frame_count = 0

    print("动画特性: 眨眼 + 呼吸 + 瞳孔平滑移动")
    print("状态: IDLE (等待用户正对)")
    print("-" * 50)

    try:
        while True:
            os.exitpoint()

            # 获取摄像头帧
            img = pl.get_frame()

            # 人脸检测
            det_boxes = face_det.run(img)

            face_detected = False
            yaw = 0
            face_cx, face_cy = 0, 0

            if det_boxes:
                # 取最大的人脸
                max_area = 0
                for det in det_boxes:
                    area = det[2] * det[3]
                    if area > max_area:
                        max_area = area
                        main_det = det

                # 姿态估计
                face_pose.config_preprocess(main_det)
                R, euler = face_pose.run(img)
                pitch, yaw, roll = euler

                face_detected = True
                face_cx = main_det[0] + main_det[2] / 2
                face_cy = main_det[1] + main_det[3] / 2

            # 状态机逻辑
            if state == "IDLE":
                pet.set_expression("sleepy")
                pet.set_eye_target(0, 0)

                if face_detected and abs(yaw) < WAKE_YAW_THRESHOLD:
                    state = "ACTIVE"
                    exit_counter = 0
                    print(">>> 唤醒! 状态: ACTIVE")

            elif state == "ACTIVE":
                if face_detected:
                    # 眼睛跟随人脸
                    pet.look_at_face(face_cx, face_cy, RGB888P_SIZE[0], RGB888P_SIZE[1])

                    if abs(yaw) < WAKE_YAW_THRESHOLD:
                        pet.set_expression("happy")
                        exit_counter = 0
                    elif abs(yaw) > EXIT_YAW_THRESHOLD:
                        pet.set_expression("curious")
                        exit_counter += 1
                        if exit_counter > EXIT_TIMEOUT_FRAMES:
                            state = "IDLE"
                            print(">>> 退出! 状态: IDLE")
                    else:
                        pet.set_expression("neutral")
                        exit_counter = 0
                else:
                    # 没检测到人脸
                    exit_counter += 1
                    if exit_counter > EXIT_TIMEOUT_FRAMES:
                        state = "IDLE"
                        print(">>> 无人脸, 退出! 状态: IDLE")

            # 渲染桌宠（高性能）
            pet_img = pet.render()

            # 复制到 OSD 层显示
            pl.osd_img.copy_from(pet_img)
            pl.show_image()

            # 每秒打印一次状态
            frame_count += 1
            if frame_count % 30 == 0 and face_detected:
                status = "正对" if abs(yaw) < WAKE_YAW_THRESHOLD else "侧脸"
                print(f"[{state}] Yaw={yaw:5.1f} [{status}]")

            gc.collect()

    except Exception as e:
        print(f"异常: {e}")
    finally:
        print("清理资源...")
        face_det.deinit()
        face_pose.deinit()
        pl.destroy()
        print("完成")
