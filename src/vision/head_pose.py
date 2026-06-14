# 头部朝向检测模块 (基于立创官方示例)

from libs.PipeLine import PipeLine, ScopedTiming
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
import os
import ujson
from media.media import *
from time import *
import nncase_runtime as nn
import ulab.numpy as np
import time
import image
import aidemo
import random
import gc
import sys


# 自定义人脸检测任务类
class FaceDetApp(AIBase):
    def __init__(self, kmodel_path, model_input_size, anchors,
                 confidence_threshold=0.25, nms_threshold=0.3,
                 rgb888p_size=[1280, 720], display_size=[1920, 1080], debug_mode=0):
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
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
                                  np.uint8, np.uint8)

    def config_preprocess(self, input_image_size=None):
        with ScopedTiming("set preprocess config", self.debug_mode > 0):
            ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
            self.ai2d.pad(self.get_pad_param(), 0, [104, 117, 123])
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            self.ai2d.build([1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                           [1, 3, self.model_input_size[1], self.model_input_size[0]])

    def postprocess(self, results):
        with ScopedTiming("postprocess", self.debug_mode > 0):
            res = aidemo.face_det_post_process(self.confidence_threshold,
                                                self.nms_threshold,
                                                self.model_input_size[0],
                                                self.anchors,
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
        top = int(round(0))
        bottom = int(round(dh * 2 + 0.1))
        left = int(round(0))
        right = int(round(dw * 2 - 0.1))
        return [0, 0, 0, 0, top, bottom, left, right]


# 自定义人脸姿态任务类
class FacePoseApp(AIBase):
    def __init__(self, kmodel_path, model_input_size,
                 rgb888p_size=[1920, 1080], display_size=[1920, 1080], debug_mode=0):
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.debug_mode = debug_mode
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
                                  np.uint8, np.uint8)

    def config_preprocess(self, det, input_image_size=None):
        with ScopedTiming("set preprocess config", self.debug_mode > 0):
            ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
            matrix_dst = self.get_affine_matrix(det)
            self.ai2d.affine(nn.interp_method.cv2_bilinear, 0, 0, 127, 1, matrix_dst)
            self.ai2d.build([1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                           [1, 3, self.model_input_size[1], self.model_input_size[0]])

    def postprocess(self, results):
        with ScopedTiming("postprocess", self.debug_mode > 0):
            R, eular = self.get_euler(results[0][0])
            return R, eular

    def get_affine_matrix(self, bbox):
        with ScopedTiming("get_affine_matrix", self.debug_mode > 1):
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
            affine_matrix = [scale, 0, cx, 0, scale, cy]
            return affine_matrix

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
        eular = self.rotation_matrix_to_euler_angles(R)
        return R, eular


# 人脸朝向检测封装类
class HeadPoseDetector:
    """头部朝向检测器 - 用于桌宠唤醒判断"""

    def __init__(self, rgb888p_size=[1920, 1080], display_size=[800, 480],
                 confidence_threshold=0.5, nms_threshold=0.2, debug_mode=0):
        # 模型路径
        self.face_det_kmodel = "/sdcard/examples/kmodel/face_detection_320.kmodel"
        self.face_pose_kmodel = "/sdcard/examples/kmodel/face_pose.kmodel"
        self.anchors_path = "/sdcard/examples/utils/prior_data_320.bin"

        # 模型输入尺寸
        self.det_input_size = [320, 320]
        self.pose_input_size = [120, 120]

        # 阈值
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold

        # 分辨率
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.debug_mode = debug_mode

        # 加载anchors
        anchor_len = 4200
        det_dim = 4
        self.anchors = np.fromfile(self.anchors_path, dtype=np.float)
        self.anchors = self.anchors.reshape((anchor_len, det_dim))

        # 初始化模型
        self.face_det = FaceDetApp(
            self.face_det_kmodel,
            model_input_size=self.det_input_size,
            anchors=self.anchors,
            confidence_threshold=self.confidence_threshold,
            nms_threshold=self.nms_threshold,
            rgb888p_size=rgb888p_size,
            display_size=display_size,
            debug_mode=0
        )
        self.face_pose = FacePoseApp(
            self.face_pose_kmodel,
            model_input_size=self.pose_input_size,
            rgb888p_size=rgb888p_size,
            display_size=display_size
        )

        # 配置人脸检测预处理
        self.face_det.config_preprocess()

    def detect(self, input_np):
        """
        检测人脸并返回朝向信息

        Args:
            input_np: 摄像头图像 (来自 pl.get_frame())

        Returns:
            list: 检测结果列表，每个元素为:
                  {
                      'box': [x, y, w, h],      # 人脸框
                      'center': (cx, cy),       # 人脸中心
                      'euler': [pitch, yaw, roll],  # 欧拉角
                      'is_facing': bool         # 是否正对摄像头
                  }
        """
        results = []

        # 人脸检测
        det_boxes = self.face_det.run(input_np)

        for det_box in det_boxes:
            # 对每个人脸进行姿态估计
            self.face_pose.config_preprocess(det_box)
            R, euler = self.face_pose.run(input_np)

            # 提取人脸框信息
            x, y, w, h = det_box[:4]
            cx = x + w / 2
            cy = y + h / 2

            # 欧拉角: [pitch, yaw, roll]
            pitch, yaw, roll = euler

            results.append({
                'box': [x, y, w, h],
                'center': (cx, cy),
                'euler': euler,
                'pitch': pitch,  # 俯仰角：抬头(+) / 低头(-)
                'yaw': yaw,      # 偏航角：左转(+) / 右转(-)
                'roll': roll,    # 翻滚角：左倾(+) / 右倾(-)
                'confidence': det_box[4] if len(det_box) > 4 else 1.0,
            })

        return results

    def get_primary_face(self, results):
        """
        获取主要人脸（面积最大的）

        Returns:
            dict or None: 主要人脸信息，如果没有检测到人脸返回None
        """
        if not results:
            return None

        # 按人脸面积排序，返回最大的
        return max(results, key=lambda r: r['box'][2] * r['box'][3])

    def is_facing_camera(self, euler, yaw_threshold=20, pitch_threshold=30):
        """
        判断是否正对摄像头

        Args:
            euler: [pitch, yaw, roll] 欧拉角
            yaw_threshold: yaw角度阈值（左右转头）
            pitch_threshold: pitch角度阈值（抬头低头）

        Returns:
            bool: 是否正对摄像头
        """
        pitch, yaw, roll = euler
        return abs(yaw) < yaw_threshold and abs(pitch) < pitch_threshold

    def deinit(self):
        """释放资源"""
        self.face_det.deinit()
        self.face_pose.deinit()


# ============ 测试代码 ============
if __name__ == "__main__":

    print("=" * 40)
    print("头部朝向检测测试")
    print("=" * 40)

    # 显示配置
    display_mode = "lcd"
    rgb888p_size = [1920, 1080]
    display_size = [800, 480]

    # 初始化PipeLine
    pl = PipeLine(rgb888p_size=rgb888p_size,
                  display_size=display_size,
                  display_mode=display_mode)
    pl.create()

    # 初始化头部检测器
    detector = HeadPoseDetector(rgb888p_size=rgb888p_size,
                                 display_size=display_size)

    print("开始检测头部朝向...")
    print("Pitch: 俯仰角 (抬头+/低头-)")
    print("Yaw:   偏航角 (左转+/右转-)")
    print("Roll:  翻滚角 (左倾+/右倾-)")
    print("-" * 40)

    try:
        while True:
            os.exitpoint()

            with ScopedTiming("total", 1):
                # 获取摄像头帧
                img = pl.get_frame()

                # 检测人脸朝向
                results = detector.detect(img)

                # 清空OSD
                pl.osd_img.clear()

                if results:
                    # 获取主要人脸
                    face = detector.get_primary_face(results)

                    # 判断是否正对摄像头
                    is_facing = detector.is_facing_camera(face['euler'])

                    # 显示信息
                    info = f"Pitch:{face['pitch']:.1f} Yaw:{face['yaw']:.1f} Roll:{face['roll']:.1f}"
                    status = "FACING" if is_facing else "NOT FACING"
                    color = (0, 255, 0, 255) if is_facing else (255, 0, 0, 255)

                    pl.osd_img.draw_string_advanced(10, 10, 24, info,
                                                    color=(255, 255, 255, 255))
                    pl.osd_img.draw_string_advanced(10, 40, 32, status, color=color)

                    # 画人脸框
                    x, y, w, h = face['box']
                    # 坐标转换到显示尺寸
                    x = int(x / rgb888p_size[0] * display_size[0])
                    y = int(y / rgb888p_size[1] * display_size[1])
                    w = int(w / rgb888p_size[0] * display_size[0])
                    h = int(h / rgb888p_size[1] * display_size[1])
                    pl.osd_img.draw_rectangle(x, y, w, h, color=color, thickness=3)

                else:
                    pl.osd_img.draw_string_advanced(10, 10, 32, "No face detected",
                                                    color=(255, 255, 0, 255))

                # 显示
                pl.show_image()
                gc.collect()

    except KeyboardInterrupt:
        print("用户退出")
    except Exception as e:
        print(f"错误: {e}")
        sys.print_exception(e)
    finally:
        print("清理资源...")
        detector.deinit()
        pl.destroy()
        print("完成")
