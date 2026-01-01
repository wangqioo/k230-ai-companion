# LCD 简单测试程序 (基于官方PipeLine)

from libs.PipeLine import PipeLine, ScopedTiming
from media.media import *
import time
import image
import os
import gc
import sys

print("=" * 40)
print("LCD 显示测试 (PipeLine)")
print("=" * 40)

# 显示配置
display_mode = "lcd"
rgb888p_size = [1920, 1080]
display_size = [800, 480]

try:
    # 1. 初始化PipeLine
    print("[1/3] 初始化 PipeLine...")
    pl = PipeLine(rgb888p_size=rgb888p_size,
                  display_size=display_size,
                  display_mode=display_mode)
    pl.create()

    print("[2/3] 绘制测试图形...")

    # 2. 在osd_img上绘制
    # pl.osd_img 是 ARGB8888 格式的图像
    pl.osd_img.clear()

    # 填充背景
    pl.osd_img.draw_rectangle(0, 0, 800, 480,
                              color=(40, 44, 52, 255), thickness=-1)

    # 红色矩形
    pl.osd_img.draw_rectangle(50, 50, 200, 150,
                              color=(255, 0, 0, 255), thickness=-1)

    # 绿色圆形
    pl.osd_img.draw_circle(400, 240, 100,
                           color=(0, 255, 0, 255), thickness=-1)

    # 蓝色矩形
    pl.osd_img.draw_rectangle(550, 280, 200, 150,
                              color=(0, 0, 255, 255), thickness=-1)

    # 添加文字
    pl.osd_img.draw_string_advanced(250, 180, 32,
                                    "Hello K230!",
                                    color=(255, 255, 255, 255))
    pl.osd_img.draw_string_advanced(260, 230, 24,
                                    "LCD Test OK",
                                    color=(255, 255, 0, 255))
    pl.osd_img.draw_string_advanced(200, 280, 20,
                                    "庐山派桌宠项目",
                                    color=(0, 255, 255, 255))

    print("[3/3] 显示测试图像...")

    print("")
    print("✓ LCD 初始化成功!")
    print("✓ 如果屏幕上显示彩色图形和文字，说明LCD工作正常")
    print("")
    print("按 Ctrl+C 退出...")

    # 持续显示
    while True:
        os.exitpoint()
        pl.show_image()
        time.sleep_ms(100)
        gc.collect()

except Exception as e:
    print(f"错误: {e}")
    sys.print_exception(e)

finally:
    print("清理资源...")
    pl.destroy()
    print("完成")
