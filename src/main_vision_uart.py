"""
K230 visual coprocessor entry point.

Deploy src/ to /sdcard/pet and run:
    exec(open('/sdcard/pet/main_vision_uart.py').read())
"""

import gc
import os
import sys
import time

from machine import FPIOA, UART
from libs.PipeLine import PipeLine

from transport.uart_publisher import VisionPublisher
from vision.head_pose import HeadPoseDetector
from vision.visual_observation import select_primary_face


UART_BAUDRATE = 921600
UART_TX_PIN = 11
UART_RX_PIN = 12
FRAME_SIZE = [1920, 1080]
HEARTBEAT_INTERVAL_MS = 1000
FACE_LOST_REPEAT_MS = 500


def ticks_ms():
    return time.ticks_ms()


def init_uart():
    fpioa = FPIOA()
    fpioa.set_function(UART_TX_PIN, FPIOA.UART2_TXD)
    fpioa.set_function(UART_RX_PIN, FPIOA.UART2_RXD)
    return UART(UART.UART2, baudrate=UART_BAUDRATE)


def run():
    os.exitpoint(os.EXITPOINT_ENABLE)
    uart = init_uart()
    publisher = VisionPublisher(uart)
    pipeline = PipeLine(
        rgb888p_size=FRAME_SIZE,
        display_size=[800, 480],
        display_mode="lcd",
    )
    detector = None
    last_heartbeat = ticks_ms()
    last_face_lost = -FACE_LOST_REPEAT_MS

    try:
        pipeline.create()
        detector = HeadPoseDetector(
            rgb888p_size=FRAME_SIZE,
            display_size=[800, 480],
            confidence_threshold=0.5,
            nms_threshold=0.2,
        )

        while True:
            os.exitpoint()
            now = ticks_ms()
            frame = pipeline.get_frame()
            primary = select_primary_face(detector.detect(frame))

            if primary:
                publisher.publish_face(
                    frame_width=FRAME_SIZE[0],
                    frame_height=FRAME_SIZE[1],
                    box=primary["box"],
                    euler=primary["euler"],
                    confidence=primary.get("confidence", 100),
                    timestamp_ms=now,
                )
            elif time.ticks_diff(now, last_face_lost) >= FACE_LOST_REPEAT_MS:
                publisher.publish_face_lost(now)
                last_face_lost = now

            if time.ticks_diff(now, last_heartbeat) >= HEARTBEAT_INTERVAL_MS:
                publisher.publish_heartbeat(now)
                last_heartbeat = now

            gc.collect()
    except Exception as error:
        try:
            publisher.publish_error(1, ticks_ms())
        except Exception:
            pass
        sys.print_exception(error)
        raise
    finally:
        if detector:
            detector.deinit()
        pipeline.destroy()
        try:
            uart.deinit()
        except Exception:
            pass


if __name__ == "__main__":
    run()
