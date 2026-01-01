# 人脸朝向检测测试 (基于立创官方例程，加入角度打印)

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
    def __init__(self,kmodel_path,model_input_size,anchors,confidence_threshold=0.25,nms_threshold=0.3,rgb888p_size=[1280,720],display_size=[1920,1080],debug_mode=0):
        super().__init__(kmodel_path,model_input_size,rgb888p_size,debug_mode)
        self.kmodel_path=kmodel_path
        self.model_input_size=model_input_size
        self.confidence_threshold=confidence_threshold
        self.nms_threshold=nms_threshold
        self.anchors=anchors
        self.rgb888p_size=[ALIGN_UP(rgb888p_size[0],16),rgb888p_size[1]]
        self.display_size=[ALIGN_UP(display_size[0],16),display_size[1]]
        self.debug_mode=debug_mode
        self.ai2d=Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)

    def config_preprocess(self,input_image_size=None):
        with ScopedTiming("set preprocess config",self.debug_mode > 0):
            ai2d_input_size=input_image_size if input_image_size else self.rgb888p_size
            self.ai2d.pad(self.get_pad_param(), 0, [104,117,123])
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],[1,3,self.model_input_size[1],self.model_input_size[0]])

    def postprocess(self,results):
        with ScopedTiming("postprocess",self.debug_mode > 0):
            res = aidemo.face_det_post_process(self.confidence_threshold,self.nms_threshold,self.model_input_size[0],self.anchors,self.rgb888p_size,results)
            if len(res)==0:
                return res
            else:
                return res[0]

    def get_pad_param(self):
        dst_w = self.model_input_size[0]
        dst_h = self.model_input_size[1]
        ratio_w = dst_w / self.rgb888p_size[0]
        ratio_h = dst_h / self.rgb888p_size[1]
        if ratio_w < ratio_h:
            ratio = ratio_w
        else:
            ratio = ratio_h
        new_w = (int)(ratio * self.rgb888p_size[0])
        new_h = (int)(ratio * self.rgb888p_size[1])
        dw = (dst_w - new_w) / 2
        dh = (dst_h - new_h) / 2
        top = (int)(round(0))
        bottom = (int)(round(dh * 2 + 0.1))
        left = (int)(round(0))
        right = (int)(round(dw * 2 - 0.1))
        return [0,0,0,0,top, bottom, left, right]

# 自定义人脸姿态任务类
class FacePoseApp(AIBase):
    def __init__(self,kmodel_path,model_input_size,rgb888p_size=[1920,1080],display_size=[1920,1080],debug_mode=0):
        super().__init__(kmodel_path,model_input_size,rgb888p_size,debug_mode)
        self.kmodel_path=kmodel_path
        self.model_input_size=model_input_size
        self.rgb888p_size=[ALIGN_UP(rgb888p_size[0],16),rgb888p_size[1]]
        self.display_size=[ALIGN_UP(display_size[0],16),display_size[1]]
        self.debug_mode=debug_mode
        self.ai2d=Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)

    def config_preprocess(self,det,input_image_size=None):
        with ScopedTiming("set preprocess config",self.debug_mode > 0):
            ai2d_input_size=input_image_size if input_image_size else self.rgb888p_size
            matrix_dst = self.get_affine_matrix(det)
            self.ai2d.affine(nn.interp_method.cv2_bilinear,0, 0, 127, 1,matrix_dst)
            self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],[1,3,self.model_input_size[1],self.model_input_size[0]])

    def postprocess(self,results):
        with ScopedTiming("postprocess",self.debug_mode > 0):
            R,eular = self.get_euler(results[0][0])
            return R,eular

    def get_affine_matrix(self,bbox):
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

    def rotation_matrix_to_euler_angles(self,R):
        sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
        if sy < 1e-6:
            pitch = np.arctan2(-R[1, 2], R[1, 1]) * 180 / np.pi
            yaw = np.arctan2(-R[2, 0], sy) * 180 / np.pi
            roll = 0
        else:
            pitch = np.arctan2(R[2, 1], R[2, 2]) * 180 / np.pi
            yaw = np.arctan2(-R[2, 0], sy) * 180 / np.pi
            roll = np.arctan2(R[1, 0], R[0, 0]) * 180 / np.pi
        return [pitch,yaw,roll]

    def get_euler(self,data):
        R = data[:3, :3].copy()
        eular = self.rotation_matrix_to_euler_angles(R)
        return R,eular

# 人脸姿态任务类
class FacePose:
    def __init__(self,face_det_kmodel,face_pose_kmodel,det_input_size,pose_input_size,anchors,confidence_threshold=0.25,nms_threshold=0.3,rgb888p_size=[1280,720],display_size=[1920,1080],debug_mode=0):
        self.face_det_kmodel=face_det_kmodel
        self.face_pose_kmodel=face_pose_kmodel
        self.det_input_size=det_input_size
        self.pose_input_size=pose_input_size
        self.anchors=anchors
        self.confidence_threshold=confidence_threshold
        self.nms_threshold=nms_threshold
        self.rgb888p_size=[ALIGN_UP(rgb888p_size[0],16),rgb888p_size[1]]
        self.display_size=[ALIGN_UP(display_size[0],16),display_size[1]]
        self.debug_mode=debug_mode
        self.face_det=FaceDetApp(self.face_det_kmodel,model_input_size=self.det_input_size,anchors=self.anchors,confidence_threshold=self.confidence_threshold,nms_threshold=self.nms_threshold,rgb888p_size=self.rgb888p_size,display_size=self.display_size,debug_mode=0)
        self.face_pose=FacePoseApp(self.face_pose_kmodel,model_input_size=self.pose_input_size,rgb888p_size=self.rgb888p_size,display_size=self.display_size)
        self.face_det.config_preprocess()

    def run(self,input_np):
        det_boxes=self.face_det.run(input_np)
        pose_res=[]
        for det_box in det_boxes:
            self.face_pose.config_preprocess(det_box)
            R,eular=self.face_pose.run(input_np)
            pose_res.append((R,eular))
        return det_boxes,pose_res

    def draw_result(self,pl,dets,pose_res):
        pl.osd_img.clear()
        if dets:
            draw_img_np = np.zeros((self.display_size[1],self.display_size[0],4),dtype=np.uint8)
            draw_img=image.Image(self.display_size[0], self.display_size[1], image.ARGB8888,alloc=image.ALLOC_REF,data=draw_img_np)
            line_color = np.array([255, 0, 0 ,255],dtype=np.uint8)
            for i,det in enumerate(dets):
                projections,center_point = self.build_projection_matrix(det)
                R,euler = pose_res[i]
                first_points = []
                second_points = []
                for pp in range(8):
                    sum_x, sum_y = 0.0, 0.0
                    for cc in range(3):
                        sum_x += projections[pp][cc] * R[cc][0]
                        sum_y += projections[pp][cc] * (-R[cc][1])
                    center_x,center_y = center_point[0],center_point[1]
                    x = (sum_x + center_x) / self.rgb888p_size[0] * self.display_size[0]
                    y = (sum_y + center_y) / self.rgb888p_size[1] * self.display_size[1]
                    x = max(0, min(x, self.display_size[0]))
                    y = max(0, min(y, self.display_size[1]))
                    if pp < 4:
                        first_points.append((x, y))
                    else:
                        second_points.append((x, y))
                first_points = np.array(first_points,dtype=np.float)
                aidemo.polylines(draw_img_np,first_points,True,line_color,2,8,0)
                second_points = np.array(second_points,dtype=np.float)
                aidemo.polylines(draw_img_np,second_points,True,line_color,2,8,0)
                for ll in range(4):
                    x0, y0 = int(first_points[ll][0]),int(first_points[ll][1])
                    x1, y1 = int(second_points[ll][0]),int(second_points[ll][1])
                    draw_img.draw_line(x0, y0, x1, y1, color = (255, 0, 0 ,255), thickness = 2)
            pl.osd_img.copy_from(draw_img)

    def build_projection_matrix(self,det):
        x1, y1, w, h = map(lambda x: int(round(x, 0)), det[:4])
        center_x = x1 + w / 2.0
        center_y = y1 + h / 2.0
        rear_width = 0.5 * w
        rear_height = 0.5 * h
        rear_depth = 0
        factor = np.sqrt(2.0)
        front_width = factor * rear_width
        front_height = factor * rear_height
        front_depth = factor * rear_width
        temp = [
            [-rear_width, -rear_height, rear_depth],
            [-rear_width, rear_height, rear_depth],
            [rear_width, rear_height, rear_depth],
            [rear_width, -rear_height, rear_depth],
            [-front_width, -front_height, front_depth],
            [-front_width, front_height, front_depth],
            [front_width, front_height, front_depth],
            [front_width, -front_height, front_depth]
        ]
        projections = np.array(temp)
        return projections, (center_x, center_y)


if __name__=="__main__":
    # 显示模式
    display_mode="lcd"
    rgb888p_size = [1920, 1080]

    if display_mode=="hdmi":
        display_size=[1920,1080]
    else:
        display_size=[800,480]

    # 模型路径
    face_det_kmodel_path="/sdcard/examples/kmodel/face_detection_320.kmodel"
    face_pose_kmodel_path="/sdcard/examples/kmodel/face_pose.kmodel"
    anchors_path="/sdcard/examples/utils/prior_data_320.bin"

    # 参数
    face_det_input_size=[320,320]
    face_pose_input_size=[120,120]
    confidence_threshold=0.5
    nms_threshold=0.2
    anchor_len=4200
    det_dim=4
    anchors = np.fromfile(anchors_path, dtype=np.float)
    anchors = anchors.reshape((anchor_len,det_dim))

    # 初始化
    pl=PipeLine(rgb888p_size=rgb888p_size,display_size=display_size,display_mode=display_mode)
    pl.create()
    fp=FacePose(face_det_kmodel_path,face_pose_kmodel_path,det_input_size=face_det_input_size,pose_input_size=face_pose_input_size,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,rgb888p_size=rgb888p_size,display_size=display_size)

    print("=" * 50)
    print("人脸朝向检测测试")
    print("=" * 50)
    print("Pitch: 俯仰角 (抬头+/低头-)")
    print("Yaw:   偏航角 (左转+/右转-)")
    print("Roll:  翻滚角 (左倾+/右倾-)")
    print("-" * 50)

    try:
        while True:
            os.exitpoint()
            with ScopedTiming("total",1):
                img=pl.get_frame()
                det_boxes,pose_res=fp.run(img)

                # ===== 打印角度数值 =====
                if det_boxes:
                    for i, det_box in enumerate(det_boxes):
                        pitch, yaw, roll = pose_res[i][1]
                        # 判断是否正对摄像头
                        is_facing = abs(yaw) < 20 and abs(pitch) < 30
                        status = "正对" if is_facing else "侧脸"
                        print("Face {}: Pitch={:6.1f}, Yaw={:6.1f}, Roll={:6.1f} [{}]".format(
                            i, pitch, yaw, roll, status))

                fp.draw_result(pl,det_boxes,pose_res)
                pl.show_image()
                gc.collect()
    except Exception as e:
        sys.print_exception(e)
    finally:
        fp.face_det.deinit()
        fp.face_pose.deinit()
        pl.destroy()
