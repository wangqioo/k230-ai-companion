"""
K230 local performance probe.

Deploy/run from CanMV IDE, or save to /sdcard/pet/perf_probe.py and run:
    exec(open('/sdcard/pet/perf_probe.py').read())

This script avoids cloud APIs. It measures:
- basic CPU loop throughput
- GC pause
- ARGB8888 image drawing throughput
- LCD display frame throughput when Display is available
- optional HTTP /ping latency to the local PC probe server
"""

import gc
import math
import time

SERVER_IP = "192.168.1.8"
SERVER_PORT = 8080

DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
FRAMES = 120


def now_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def diff_ms(end, start):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(end, start)
    return end - start


def section(name):
    print("")
    print("=" * 48)
    print(name)
    print("=" * 48)


def cpu_probe():
    section("CPU LOOP")
    total = 0
    start = now_ms()
    for i in range(250000):
        total += (i * 17) % 97
    elapsed = diff_ms(now_ms(), start)
    print("iterations: 250000")
    print("elapsed_ms:", elapsed)
    print("checksum:", total)
    if elapsed > 0:
        print("iter_per_sec:", int(250000 * 1000 / elapsed))


def gc_probe():
    section("GC")
    payload = []
    for i in range(600):
        payload.append(bytearray(512))
    before = gc.mem_free() if hasattr(gc, "mem_free") else -1
    start = now_ms()
    gc.collect()
    elapsed = diff_ms(now_ms(), start)
    after = gc.mem_free() if hasattr(gc, "mem_free") else -1
    print("gc_ms:", elapsed)
    print("mem_free_before:", before)
    print("mem_free_after:", after)


def draw_face(img, frame):
    img.clear()
    img.draw_rectangle(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT,
                       color=(35, 38, 45, 255), thickness=-1, fill=True)
    breath = int(math.sin(frame * 0.12) * 4)
    blink = 1
    if frame % 70 in (0, 1, 2, 3):
        blink = 8

    left_x = 320
    right_x = 480
    eye_y = 210 + breath
    pupil_dx = int(math.sin(frame * 0.07) * 18)
    pupil_dy = int(math.cos(frame * 0.05) * 10)

    for x in (left_x, right_x):
        img.draw_ellipse(x, eye_y, 55, max(8, 45 // blink), 0, 0, 360,
                         color=(255, 255, 255, 255), thickness=-1, fill=True)
        if blink == 1:
            img.draw_circle(x + pupil_dx, eye_y + pupil_dy, 22,
                            color=(40, 44, 52, 255), thickness=-1, fill=True)
            img.draw_circle(x + pupil_dx - 7, eye_y + pupil_dy - 7, 6,
                            color=(255, 255, 255, 255), thickness=-1, fill=True)

    mouth_y = 335 + breath
    for x in range(-32, 33, 8):
        y = int((x * x) / 50)
        img.draw_circle(400 + x, mouth_y + y, 4,
                        color=(255, 120, 120, 255), thickness=-1, fill=True)


def graphics_probe():
    section("GRAPHICS")
    try:
        import image
    except Exception as e:
        print("image import failed:", e)
        return None

    img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)
    start = now_ms()
    for frame in range(FRAMES):
        draw_face(img, frame)
    elapsed = diff_ms(now_ms(), start)
    print("draw_frames:", FRAMES)
    print("draw_elapsed_ms:", elapsed)
    if elapsed > 0:
        print("draw_fps:", round(FRAMES * 1000 / elapsed, 2))
    return img


def display_probe(img):
    section("DISPLAY")
    if img is None:
        print("skipped: no image")
        return
    try:
        from media.display import Display
        from media.media import MediaManager
    except Exception as e:
        print("display import failed:", e)
        return

    try:
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
        MediaManager.init()
        start = now_ms()
        for frame in range(FRAMES):
            draw_face(img, frame)
            Display.show_image(img, 0, 0, Display.LAYER_OSD3)
        elapsed = diff_ms(now_ms(), start)
        print("display_frames:", FRAMES)
        print("display_elapsed_ms:", elapsed)
        if elapsed > 0:
            print("display_fps:", round(FRAMES * 1000 / elapsed, 2))
        time.sleep(2)
        Display.deinit()
        MediaManager.deinit()
    except Exception as e:
        print("display probe failed:", e)


def http_probe():
    section("HTTP PING")
    try:
        import socket
        from network import WLAN
    except Exception as e:
        print("network import failed:", e)
        return

    wlan = WLAN(0)
    if not wlan.isconnected():
        print("wifi not connected; run src/network/test_wifi.py first or connect in boot config")
        return

    print("device_ip:", wlan.ifconfig()[0])
    addr = socket.getaddrinfo(SERVER_IP, SERVER_PORT)[0][-1]
    times = []
    for i in range(5):
        try:
            start = now_ms()
            s = socket.socket()
            s.settimeout(5)
            s.connect(addr)
            req = "GET /ping HTTP/1.1\r\nHost: " + SERVER_IP + "\r\nConnection: close\r\n\r\n"
            s.send(req.encode())
            data = s.recv(512)
            s.close()
            elapsed = diff_ms(now_ms(), start)
            times.append(elapsed)
            print("ping", i + 1, "ms:", elapsed, "bytes:", len(data))
        except Exception as e:
            print("ping", i + 1, "failed:", e)
    if times:
        print("ping_min_ms:", min(times))
        print("ping_avg_ms:", round(sum(times) / len(times), 2))


def main():
    print("K230 PERF PROBE")
    print("server:", SERVER_IP + ":" + str(SERVER_PORT))
    if hasattr(gc, "mem_free"):
        print("mem_free_start:", gc.mem_free())
    cpu_probe()
    gc_probe()
    img = graphics_probe()
    display_probe(img)
    http_probe()
    if hasattr(gc, "mem_free"):
        print("mem_free_end:", gc.mem_free())
    print("")
    print("PERF PROBE DONE")


main()
