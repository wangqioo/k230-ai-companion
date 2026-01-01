# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains K230 chip development resources:
1. **MicroPython Development** - Using CanMV on the LuShan-Pi K230 development board (primary focus)
2. **K230 SDK** - Native C/Linux/RT-Smart development toolkit in `k230_sdk/` directory

The K230 is a RISC-V based dual-core SoC with hardware AI acceleration capabilities (KPU - Knowledge Processing Unit).

## Hardware Platform

**Board**: LuShan-Pi K230 CanMV Development Board
- **Processor**: K230 dual-core RISC-V SoC (RT-Smart on big core)
- **GPIO**: 64 GPIO pins with FPIOA (flexible pin multiplexing)
- **Peripherals**:
  - PWM: 6 channels (0-5), grouped in pairs sharing frequency
  - UART: 5 hardware modules (UART0-4), UART0 reserved for RT-Smart console
  - ADC: 6 channels, 12-bit resolution, 1MHz sampling, **1.8V max input**
  - I2C: Multiple channels with hardware pullups
  - SPI: Available on 40-pin header
  - RTC: Real-time clock (no backup battery on board)
  - WDT: 2 watchdog timers (only WDT1 available to users)

**Critical Hardware Constraints**:
- ADC pins accept **maximum 1.8V** - exceeding this damages the board permanently
- RGB LED uses shared-anode configuration (HIGH=off, LOW=on)
- PWM channels 0,1,2 share frequency; channels 3,4,5 share frequency
- Onboard buzzer uses PWM1, LCD backlight uses PWM5
- UART0 reserved for RT-Smart system console (115200 baud)
- Boot from SD card; flashing new firmware requires re-imaging the SD card

## Pin Mapping Reference

**RGB LED (Shared Anode)**:
- Red: GPIO62, Green: GPIO20, Blue: GPIO63

**User Button**:
- GPIO53 (active HIGH with internal pulldown)

**Buzzer**:
- GPIO43 (PWM1, resonant at 4000Hz)

**Key Serial Interfaces**:
- UART2: GPIO11 (TX), GPIO12 (RX) - Primary user serial port (GH1.25 connector)
- UART3: GPIO50 (TX), GPIO51 (RX) - Available for user
- I2C0: GPIO48 (SCL), GPIO49 (SDA) - Shared with CSI camera
- I2C1: GPIO40 (SCL), GPIO41 (SDA) - Shared with CSI camera

**ADC Channels**: Available via 6P FPC connector (1.8V max)

**Camera Interfaces**:
- CSI2: Default camera (22P 0.5mm FPC, vertical connector on front)
- CSI0/CSI1: Additional cameras (22P 0.5mm FPC, horizontal flip connectors on back)
- Compatible with Raspberry Pi Zero/Pi 5 camera ribbon cables
- Default camera: GC2093 (1920x1080@60fps max, fixed focus 70cm for small lens)

## Development Environment

**IDE**: CanMV IDE K230
- Connect via USB (creates virtual serial port)
- Serial terminal for REPL and debug output
- File management to/from SD card

**Firmware**: CanMV K230 MicroPython
- Based on MicroPython 3 syntax
- Custom `machine` module for hardware access
- Official docs: https://developer.canaan-creative.com/k230_canmv/main/zh/

## Common Development Commands

**Basic GPIO Control**:
```python
from machine import Pin, FPIOA

# Configure pin function
fpioa = FPIOA()
fpioa.set_function(62, FPIOA.GPIO62)

# Control pin
led = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
led.low()   # Turn on (shared anode)
led.high()  # Turn off
```

**PWM Generation**:
```python
from machine import PWM, FPIOA

fpioa = FPIOA()
fpioa.set_function(47, FPIOA.PWM3)

pwm = PWM(3, freq=1000, duty_u16=32768)  # 50% duty cycle
```

**UART Communication**:
```python
from machine import UART, FPIOA

fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)

uart = UART(UART.UART2, baudrate=115200)
uart.write(b"Hello")
data = uart.read()
```

**ADC Reading** (⚠️ 1.8V max):
```python
from machine import ADC

adc = ADC(0)
value = adc.read_u16()      # Raw 12-bit value (0-4095)
voltage = adc.read_uv()     # Voltage in microvolts (0-1800000)
```

**Camera Image Capture**:
```python
from media.sensor import *
from media.display import *
from media.media import *

# Initialize sensor (default CSI2, id=2)
sensor = Sensor()  # or Sensor(id=0) for CSI0, Sensor(id=1) for CSI1
sensor.reset()

# Configure output: resolution and pixel format
sensor.set_framesize(width=800, height=480, chn=CAM_CHN_ID_0)
sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)  # or RGB888, GRAYSCALE, YUV420SP

# Initialize display (LCD/HDMI/Virtual)
Display.init(Display.ST7701, width=800, height=480, to_ide=True)
MediaManager.init()
sensor.run()

while True:
    img = sensor.snapshot(chn=CAM_CHN_ID_0)
    # Process image here
    Display.show_image(img)
```

**Image Drawing Operations**:
```python
# Draw on captured or created images
img.draw_rectangle(x, y, w, h, color=(255,0,0), thickness=2)
img.draw_circle(cx, cy, radius, color=(0,255,0), thickness=2)
img.draw_line(x0, y0, x1, y1, color=(0,0,255), thickness=2)
img.draw_string_advanced(x, y, size, "中文文字", color=(255,255,0))
```

## Code Architecture Principles

**Pin Configuration Pattern**:
1. Always configure FPIOA before using Pin/UART/PWM/etc
2. Use FPIOA.set_function() to multiplex pins
3. Check pin conflicts (e.g., PWM1 on both buzzer and header pin 26)

**Hardware Resource Management**:
- Call `.deinit()` on PWM/UART/Timer when finished
- Use `machine.reset()` for full system restart
- WDT requires periodic `feed()` calls - timeout triggers hard reset

**Thread Safety** (when using `_thread` module):
- MicroPython threads are **non-preemptive** - must call `time.sleep()` to yield
- Always use locks (`_thread.allocate_lock()`) for shared resources
- Wrap critical sections in try/finally to guarantee lock release

**LED Control Convention**:
- RGB LED is **shared-anode**: `pin.low()` turns ON, `pin.high()` turns OFF
- Always initialize all LED pins HIGH to avoid unexpected lighting

**Graphics Performance Optimization**:
- Use `image` library C functions (`draw_circle`, `draw_ellipse`, `draw_rectangle`) instead of Python loops - they're 10x faster
- Avoid pixel-by-pixel Python loops for drawing - always use the C-implemented drawing API
- For filled shapes without `fill=True` support: draw concentric circles/ellipses from outside in with `thickness=2`
- Pre-render complex graphics as PNG sprites and use `img.draw_image()` for game-like rendering
- Call `gc.collect()` regularly to prevent memory fragmentation

**Camera/Image Processing Pattern**:
1. Always call `sensor.reset()` after creating Sensor object before other operations
2. Set resolution/format before initializing Display/MediaManager
3. Call `MediaManager.init()` before `sensor.run()`
4. Call `sensor.stop()` before `Display.deinit()`
5. Call `Display.deinit()` before `MediaManager.deinit()` in cleanup
6. Most image processing APIs only support RGB565 or GRAYSCALE formats

**Display Device Selection**:
- `Display.VIRT`: IDE frame buffer (USB bandwidth limited, lower FPS/quality tradeoff)
- `Display.ST7701`: 3.1" LCD expansion board (800x480, connects via 31P MIPI)
- `Display.LT9611`: HDMI expansion board (1920x1080, connects via 31P MIPI)

## Hardware Warnings

⚠️ **CRITICAL - Read Before Connecting Hardware**:
1. **ADC Voltage Limit**: Never exceed 1.8V on ADC pins - irreversible damage
2. **No 5V Tolerance**: GPIO are 3.3V logic only
3. **Power Supply**:
   - USB-C provides 5V (no PD negotiation)
   - GH1.25 connectors provide 5V on pin 1
   - 12V DC input available (GH1.25-2P connector)
4. **Camera I2C Conflicts**: GPIO40/41 and GPIO48/49 have 4.7K pullups for cameras
5. **PWM Frequency Coupling**: Channels 0-2 share clock, channels 3-5 share clock
6. **Button Debouncing**: Hardware has no debounce - implement in software for state toggling
7. **Camera Focus**: Default small lens is fixed-focus (70cm optimal). For adjustable focus, purchase large lens version or carefully break adhesive on small lens to adjust manually
8. **WiFi Limitations**: RTL8189FTV chip supports **2.4GHz only** (no 5GHz band)
9. **Ethernet Requirement**: USB-to-Ethernet adapter (RTL8152B chip) **must be connected before power-on** to be detected
10. **Touch Screen I2C**: CST128 touch controller shares I2C bus - avoid conflicts with other I2C devices
11. **Audio Format**: Only WAV format supported - no MP3/AAC playback in current firmware

## Common Patterns

**Anti-Debounce Button Handler**:
```python
last_state = 0
last_time = 0
DEBOUNCE_MS = 20

button_state = button.value()
current_time = time.ticks_ms()

if button_state == 1 and last_state == 0:
    if current_time - last_time > DEBOUNCE_MS:
        # Handle button press
        last_time = current_time
last_state = button_state
```

**PWM Tone Generation** (for buzzer):
```python
# Music note frequencies (Hz)
notes = {'C4': 261, 'D4': 293, 'E4': 329, 'G4': 392}

def play_tone(note, duration_ms):
    beep.freq(notes[note])
    beep.duty_u16(32768)  # 50% duty
    time.sleep_ms(duration_ms)
    beep.duty_u16(0)  # Silence
```

**Watchdog Protection Pattern**:
```python
wdt = WDT(1, 10)  # 10 second timeout

while True:
    # Perform critical tasks
    wdt.feed()  # Reset watchdog
    time.sleep(1)
```

**Color Blob Detection** (LAB color space):
```python
# Define color threshold in LAB: (L_min, L_max, A_min, A_max, B_min, B_max)
red_threshold = [(0, 79, 31, 67, 26, 60)]

img = sensor.snapshot()
blobs = img.find_blobs(red_threshold, area_threshold=2000)
for blob in blobs:
    img.draw_rectangle(blob[0:4])  # x, y, w, h
    img.draw_cross(blob[5], blob[6])  # cx, cy
```

**Feature Detection**:
```python
# Line segments (LSD algorithm)
lines = img.find_line_segments(merge_distance=20, max_theta_diff=10)

# Rectangles (AprilTag quad detection)
rects = img.find_rects(threshold=5000)

# Circles (Hough transform)
circles = img.find_circles(threshold=6000)
```

**Barcode/QR Code Recognition**:
```python
# 1D Barcodes (use GRAYSCALE format)
sensor.set_pixformat(Sensor.GRAYSCALE)
for code in img.find_barcodes():
    print(code.payload())

# QR Codes
for code in img.find_qrcodes():
    print(code.payload())

# AprilTags (machine vision markers)
for tag in img.find_apriltags(families=image.TAG36H11):
    print(f"Tag ID: {tag.id()}")
```

**Touch Screen (Capacitive)** (via I2C):
```python
from machine import TOUCH

# Initialize touch screen (CST128 driver, 5-point multi-touch)
touch = TOUCH(index=0, rotation=DEGREE_0)  # rotation: DEGREE_0/90/180/270

# Read touch data in polling mode
data = touch.read()
if data and data[0].event in [1, 2]:  # 1=press, 2=move, 3=release
    x = data[0].x
    y = data[0].y
    print(f"Touch at ({x}, {y})")
```

**Video Recording** (MP4/H.264/H.265):
```python
from media.vencoder import *

# Create encoder (1=H264, 2=H265)
encoder = Encoder(ENCODE_TYPE_H264)
encoder.create(chn, width, height, profile=VENC_PROFILE_H264_MAIN)

# Configure encoder
config = VencChnAttr()
config.type = ENCODE_TYPE_H264
config.profile = VENC_PROFILE_H264_MAIN
config.pic_width = 1280
config.pic_height = 720
config.gop = 50  # GOP size
encoder.set_venc_chn_attr(chn, config)

# Bind sensor channel to encoder and start
MediaManager.link(sensor.get_link_info(chn), encoder.get_link_info())
encoder.start(chn)

# Create MP4 container
out_file = open("/sdcard/video.mp4", "wb")
encoder.bind_file(chn, out_file)

# Record... (encoder processes frames automatically)

# Stop and cleanup
encoder.stop(chn)
encoder.destroy(chn)
out_file.close()
```

**Audio Recording/Playback** (WAV):
```python
from media.audio import *

# Audio recording
ai = Audio(INPUT)
ai.set_channel_count(1)  # 1=mono, 2=stereo
ai.set_sample_rate(44100)  # 8000/16000/22050/24000/32000/44100/48000
ai.set_bit_depth(16)

wav_file = open("/sdcard/record.wav", "wb")
ai.start()
for i in range(200):  # Record ~4-5 seconds
    audio_data = ai.read()
    wav_file.write(audio_data)
ai.stop()
wav_file.close()

# Audio playback
ao = Audio(OUTPUT)
ao.set_channel_count(1)
ao.set_sample_rate(44100)

wav_file = open("/sdcard/record.wav", "rb")
ao.start()
while True:
    audio_data = wav_file.read(4096)
    if not audio_data:
        break
    ao.write(audio_data)
ao.stop()
wav_file.close()
```

**WiFi Connection** (2.4GHz only):
```python
from network import WLAN

# Station mode (connect to AP)
wlan = WLAN(0)  # 0=STA, 1=AP
wlan.connect("SSID", "password")

# Wait for connection
while not wlan.isconnected():
    time.sleep(0.1)

print(wlan.ifconfig())  # (ip, netmask, gateway, dns)

# AP mode (create hotspot)
ap = WLAN(1)
ap.config(ssid="K230_AP", key="12345678", channel=6)

# Use socket API for network communication
import socket
s = socket.socket()
s.connect(('example.com', 80))
```

**Ethernet** (USB-to-Ethernet):
```python
from network import LAN

# Requires RTL8152B USB-to-Ethernet adapter
# MUST be connected BEFORE board powers on
lan = LAN()

# Wait for link
while not lan.isconnected():
    time.sleep(0.1)

print(lan.ifconfig())  # (ip, netmask, gateway, dns)

# Static IP configuration
lan.ifconfig(("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8"))
```

## Troubleshooting

**Board Won't Connect to IDE**:
- Check USB cable supports data (not charge-only)
- Verify SD card has CanMV firmware properly flashed
- If WDT timeout too short, reflash SD card to reset

**PWM Not Working**:
- Verify pin configured via FPIOA before PWM init
- Check frequency conflicts if using PWM1 with buzzer
- Confirm duty cycle range: duty_u16(0-65535) or duty(0-100)

**UART No Data**:
- Don't use UART0 (reserved for RT-Smart console at 115200 baud)
- Cross-connect: Board TX → External RX, Board RX → External TX
- Verify baud rate match: default 115200

**ADC Reads Zero**:
- Confirm voltage is 0-1.8V (measure with multimeter first)
- Check FPC connector seated properly
- ADC channels 4-5 may not be exposed on current board revision

**Camera Not Detecting**:
- Check 22P FPC cable properly seated in connector
- Verify using correct sensor ID (CSI2=id:2, CSI0=id:0, CSI1=id:1)
- Ensure `sensor.reset()` called before configuration
- Try different resolutions if current one fails

**Image Recognition Poor Results**:
- Adjust lighting conditions - most algorithms sensitive to lighting
- Use GRAYSCALE format for barcode/QR/AprilTag detection
- Reduce resolution to improve FPS if needed (e.g., 400x240 instead of 800x480)
- For color detection: use IDE's Threshold Editor (Tools → Machine Vision → Threshold Editor)
- For feature detection: tune threshold parameters (lower=more detections, higher=fewer false positives)
- Ensure camera is in focus - default lens focuses at ~70cm distance

**Low Frame Rate**:
- Reduce image resolution
- Use GRAYSCALE instead of RGB888 when color not needed
- Disable `to_ide=True` in Display.init() if not debugging
- Some algorithms (AprilTag) are computationally intensive - expect lower FPS

**Touch Screen Not Responding**:
- Verify LCD expansion board with touch screen is connected
- Check I2C bus not in use by conflicting devices
- Call `touch.read()` in polling loop - no interrupt/event system yet
- Verify correct rotation setting (DEGREE_0/90/180/270)

**Video Recording Issues**:
- Ensure sufficient SD card space (1080p@30fps ≈ 100MB/min)
- Use Class 10 or UHS-I SD card for high bitrate recording
- GOP size affects compression - lower GOP = larger files but better seek
- Encoder automatically downscales if sensor resolution > encoder resolution

**Audio Recording Silent/Distorted**:
- Verify sample rate match between recording and playback (44100Hz recommended)
- Check microphone hardware connection (onboard mic on some board revisions)
- Audio data is raw PCM - wrap in WAV header for portability
- Use bit depth 16 (8-bit may introduce quantization noise)

**WiFi Won't Connect**:
- Verify router is 2.4GHz (5GHz not supported by RTL8189FTV)
- Check SSID/password correct (case-sensitive)
- Some enterprise WPA2 networks not supported
- Signal strength: keep router within 10m for initial testing
- Disconnect AP mode (WLAN(1)) before using STA mode (WLAN(0))

**Ethernet Not Detected**:
- Critical: USB-to-Ethernet adapter must use RTL8152B chip (verify before purchase)
- Must be connected **before** board powers on
- Check adapter LED indicators for link status
- Try different USB ports if using hub

**AI Model Inference Issues**:
- Verify kmodel file exists at specified path
- Check model input size matches Ai2d output size
- Ensure image width is 16-byte aligned with ALIGN_UP()
- Memory issues: reduce resolution or call gc.collect() more frequently
- Anchors file required for face detection (prior_data_320.bin)
- Face recognition threshold default 0.75 (adjust for accuracy vs false positives)

**PipeLine Errors**:
- Call MediaManager.init() before sensor.run()
- Create PipeLine before initializing AI task classes
- Always call pl.destroy() in finally block to release resources
- Display mode must match hardware (don't use "hdmi" if no HDMI connected)

**Ai2d Preprocessing Fails**:
- Check input/output shapes match in ai2d.build()
- Affine matrix must be 6-element list [a, b, c, d, e, f]
- Padding array format: [r, g, b, a, top, bottom, left, right]
- Crop coordinates must be within image bounds
- Call set_ai2d_dtype() before any preprocessing operations

## Key Differences from Standard MicroPython

1. **FPIOA Requirement**: Must configure pin function before use (not in standard MicroPython)
2. **PWM Channel Coupling**: Frequency shared across channel groups (hardware limitation)
3. **RGB LED Polarity**: Shared-anode requires inverted logic
4. **No Hardware Interrupts**: Pin IRQ mode not yet supported in current firmware
5. **Thread Yielding**: Must explicitly call `time.sleep()` for thread switching
6. **WDT Behavior**: Resets entire system including IDE connection
7. **Media Modules**: Custom `media.sensor`, `media.display`, `media.media`, `media.vencoder`, `media.audio` modules not in standard MicroPython
8. **Image API**: Extended `image` module with OpenMV-compatible methods plus Chinese text support
9. **Touch API**: Custom `machine.TOUCH` class (not in standard MicroPython)
10. **Network Modules**: `network.WLAN` and `network.LAN` with K230-specific limitations (2.4GHz WiFi only, RTL8152B Ethernet only)
11. **Video Encoding**: Hardware-accelerated H.264/H.265 encoding via direct sensor-to-encoder binding
12. **Audio Format**: Raw PCM with manual WAV header wrapping (no codec libraries)
13. **AI Framework**: Custom `libs.PipeLine`, `libs.AIBase`, `libs.AI2D` for AI application development (not in standard MicroPython)
14. **KPU Acceleration**: `nncase_runtime` module for kmodel inference on NPU hardware
15. **aidemo Library**: Pre-built post-processing functions for common AI tasks (face detection, pose estimation, etc.)
16. **ulab Limitations**: `ulab.numpy` is a subset of numpy with key restrictions:
   - No `mgrid` or `meshgrid` functions
   - No 2D boolean array indexing
   - No advanced fancy indexing
   - Available: `zeros()`, `ones()`, `array()`, basic math, slicing

## Image Processing Capabilities

**Pixel Format Support**:
- **RGB565**: 16-bit color (5R-6G-5B), most image APIs compatible
- **RGB888**: 24-bit color, higher quality but more memory
- **GRAYSCALE**: 8-bit monochrome, required for barcode/QR/AprilTag detection
- **YUV420SP**: Video compression format, not for image processing
- Most computer vision functions require RGB565 or GRAYSCALE

**Color Space Conversions**:
- LAB color space preferred for color blob detection (separates luminance from chrominance)
- More robust to lighting changes than RGB
- Use IDE Threshold Editor to find LAB ranges visually

**Supported Algorithms**:
- **Line Detection**: LSD (Line Segment Detector) - no pre-processing needed
- **Shape Detection**: Circles (Hough), Rectangles (AprilTag quad algorithm)
- **Color Tracking**: Blob detection in LAB space with area/pixel thresholds
- **Barcode/QR**: 1D codes (EAN, UPC, Code128, etc.), QR codes, DataMatrix
- **AprilTags**: TAG16H5, TAG25H7/H9, TAG36H10/H11, ARToolkit (for robotics/AR)

**Drawing Functions** (all support Chinese text):
- `draw_string_advanced()`: FreeType-rendered text with custom fonts
- `draw_rectangle()`, `draw_circle()`, `draw_line()`, `draw_cross()`
- `draw_arrow()`, `draw_ellipse()`, `draw_keypoints()`
- Colors specified as RGB tuples: `(R, G, B)` with values 0-255

## Multimedia Capabilities

**Touch Screen**:
- **Driver**: CST128 (FT5316 compatible)
- **Points**: 5-point capacitive multi-touch
- **Interface**: I2C
- **API**: Polling mode only (no callbacks in current firmware)
- **Events**: Press (1), Move (2), Release (3)
- **Rotation**: Configurable (0°, 90°, 180°, 270°)

**Video Recording**:
- **Codecs**: H.264 (AVC), H.265 (HEVC)
- **Container**: MP4
- **Profiles**: Baseline, Main, High (H.264); Main (H.265)
- **GOP**: Configurable (affects compression ratio and seek performance)
- **Max Resolution**: Depends on sensor (1920x1080 for GC2093)
- **Encoding**: Hardware-accelerated, real-time
- **Audio Muxing**: Automatic when both video and audio encoders bound

**Audio Recording/Playback**:
- **Format**: WAV (PCM uncompressed)
- **Sample Rates**: 8000, 16000, 22050, 24000, 32000, 44100, 48000 Hz
- **Bit Depth**: 8-bit or 16-bit
- **Channels**: Mono or stereo
- **Interface**: I2S (internal codec)
- **Limitations**: No MP3/AAC/FLAC support; raw PCM only

**WiFi Networking**:
- **Chip**: RTL8189FTV
- **Bands**: 2.4GHz only (802.11b/g/n)
- **Modes**: Station (STA), Access Point (AP)
- **Security**: WPA/WPA2-PSK (no enterprise WPA2)
- **API**: Standard MicroPython socket API
- **Libraries**: Compatible with urequests, umqtt, etc.

**Ethernet Networking**:
- **Chip**: RTL8152B (USB-to-Ethernet)
- **Interface**: USB 2.0
- **Speed**: 10/100 Mbps
- **Configuration**: DHCP or static IP
- **Requirement**: Must be connected before power-on
- **API**: Standard MicroPython socket API (same as WiFi)

## AI Development Framework

**Framework Architecture**:
The K230 provides an AI development framework built on top of the CanMV API to simplify AI application development. The framework includes:

- **PipeLine**: Manages dual video streams (one for display, one for AI processing)
- **AIBase**: Base class for AI tasks (handles kmodel loading, inference)
- **Ai2d**: Hardware-accelerated preprocessing (crop, shift, pad, resize, affine)
- **aidemo**: Post-processing utilities for common AI tasks

**Camera → AI Processing Flow**:
```
Camera (Sensor)
    ├─→ YUV420SP stream → Display (direct output)
    └─→ RGBP888 stream → AI Processing
                           ├─→ Ai2d Preprocessing
                           ├─→ KPU Inference (kmodel)
                           ├─→ Post-processing
                           └─→ Draw results on OSD → Display overlay
```

**AI Task Types**:

1. **Single Model Task**: One model with Ai2d preprocessing
   - Inherit from AIBase
   - Implement: `config_preprocess()`, `postprocess()`, `draw_result()`
   - Example: Face detection

2. **Multi-Ai2d Task**: One model with multiple preprocessing stages
   - Override `preprocess()` to chain multiple Ai2d instances
   - Example: Resize → Crop sequence

3. **Custom Preprocessing**: One model with non-Ai2d preprocessing
   - Override `preprocess()` with custom logic (ulab.numpy)
   - Example: Audio feature extraction

4. **No Preprocessing Task**: Direct model input
   - Override `run()` to skip preprocessing
   - Example: Tracking model (uses previous model output)

5. **Multi-Model Task**: Pipeline of multiple models
   - Create separate task classes for each model
   - Coordinate in main task class
   - Example: Face detection → Face recognition

**Typical AI Application Structure**:
```python
from libs.PipeLine import PipeLine, ScopedTiming
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
import nncase_runtime as nn
import ulab.numpy as np

class MyAIApp(AIBase):
    def __init__(self, kmodel_path, model_input_size, rgb888p_size=[1920,1080],
                 display_size=[1920,1080], debug_mode=0):
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        self.model_input_size = model_input_size
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,
                                  nn.ai2d_format.NCHW_FMT,
                                  np.uint8, np.uint8)

    def config_preprocess(self, input_image_size=None):
        ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
        # Configure Ai2d operations (pad, resize, etc.)
        self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
        self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],
                        [1,3,self.model_input_size[1],self.model_input_size[0]])

    def postprocess(self, results):
        # Custom post-processing logic
        return processed_results

    def draw_result(self, pl, results):
        # Draw on OSD layer
        pl.osd_img.draw_rectangle(x, y, w, h, color=(255,255,0,255), thickness=2)

# Main execution
if __name__ == "__main__":
    display_mode = "lcd"  # or "hdmi"
    rgb888p_size = [1920, 1080]
    display_size = [800, 480] if display_mode=="lcd" else [1920, 1080]

    pl = PipeLine(rgb888p_size=rgb888p_size, display_size=display_size,
                  display_mode=display_mode)
    pl.create()

    my_ai = MyAIApp(kmodel_path, model_input_size=[320, 320])
    my_ai.config_preprocess()

    try:
        while True:
            os.exitpoint()
            with ScopedTiming("total", 1):
                img = pl.get_frame()
                results = my_ai.run(img)
                my_ai.draw_result(pl, results)
                pl.show_image()
                gc.collect()
    except Exception as e:
        sys.print_exception(e)
    finally:
        my_ai.deinit()
        pl.destroy()
```

**Common AI Models (Pre-deployed in /sdcard/examples/kmodel/)**:

*Face Detection & Recognition:*
- `face_detection_320.kmodel`: Face detection (320x320 input)
- `face_recognition.kmodel`: Face feature extraction (112x112 input)
- `face_landmark.kmodel`: Facial landmark detection (192x192 input)
- `face_pose.kmodel`: Head pose estimation (120x120 input)
- `face_parse.kmodel`: Face segmentation (320x320 input)
- `face_alignment.kmodel`: 3D face mesh (120x120 input)
- `eye_gaze.kmodel`: Eye gaze direction (448x448 input)

*Person & Body Detection:*
- `person_detect_yolov5n.kmodel`: Person detection (640x640 input, YOLOv5n)
- `yolov8n-pose.kmodel`: Person keypoint detection (320x320 input, 17 keypoints)
- `yolov5n-falldown.kmodel`: Fall detection (640x640 input, Fall/NoFall classes)

*Hand Detection & Gesture:*
- `hand_det.kmodel`: Hand detection (512x512 input)
- `handkp_det.kmodel`: Hand keypoint detection (256x256 input, 21 keypoints)
- `hand_reco.kmodel`: Hand gesture recognition (224x224 input, gun/other/yeah/five)
- `gesture.kmodel`: Dynamic gesture recognition (224x224 input)

**Ai2d Preprocessing Operations**:
```python
# Padding (top, bottom, left, right)
ai2d.pad([0, 0, 0, 0, top, bottom, left, right], mode, pad_value)

# Resize
ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)

# Crop
ai2d.crop(x, y, w, h)

# Affine transformation
ai2d.affine(nn.interp_method.cv2_bilinear, 0, 0, 127, 1, affine_matrix)

# Shift (channel-wise normalization)
ai2d.shift(shift_values)

# Build preprocessing pipeline
ai2d.build(input_shape, output_shape)
```

**Important AI Framework Notes**:
- Always call `sensor.reset()` before other camera operations
- Call `MediaManager.init()` before `sensor.run()`
- Proper cleanup order: `sensor.stop()` → `Display.deinit()` → `MediaManager.deinit()`
- Use `ALIGN_UP(width, 16)` for all image widths (hardware requirement)
- OSD layer for drawing does not modify original image data
- Use `ScopedTiming` for performance profiling
- Call `gc.collect()` regularly to prevent memory fragmentation
- Face detection anchors loaded from `/sdcard/examples/utils/prior_data_320.bin`

**Face Detection + Recognition Workflow**:
1. Run face detection model to get bounding boxes
2. For each detected face:
   - Extract face region using bounding box
   - Apply affine transformation to align face (Umeyama algorithm)
   - Run face recognition model to extract 128-dim feature vector
   - Compare with database features using cosine similarity
   - Threshold typically 0.75 for face matching

**Face Registration Process**:
1. Place face images in `/sdcard/examples/utils/db_img/`
2. Run registration script to extract features
3. Features saved as `.bin` files in `/sdcard/examples/utils/db/`
4. Recognition script loads all `.bin` files into memory for matching
5. Maximum 100 registered faces supported by default

## K230 SDK (Native Development)

The `k230_sdk/` directory contains the native C SDK for low-level K230 development. This is separate from MicroPython/CanMV development.

### SDK Build Commands

**Prerequisites**:
```bash
# Pull Docker image (recommended)
docker pull ghcr.io/kendryte/k230_sdk

# Download source code and toolchains
cd k230_sdk
make prepare_sourcecode
```

**Building**:
```bash
# Enter Docker environment
docker run -u root -it -v $(pwd):$(pwd) -v $(pwd)/toolchain:/opt/toolchain -w $(pwd) ghcr.io/kendryte/k230_sdk /bin/bash

# Build for specific board
make CONF=k230_evb_defconfig        # K230 EVB board
make CONF=k230_canmv_defconfig      # CanMV-K230 board
```

**Key Make Targets**:
- `make` - Full build (Linux + RT-Smart + images)
- `make linux` - Build Linux kernel only
- `make rt-smart-kernel` - Build RT-Smart kernel only
- `make mpp` - Build Media Processing Platform (kernel + apps)
- `make uboot` - Build U-Boot bootloader
- `make buildroot` - Build Linux rootfs
- `make build-image` - Generate flashable SD card image
- `make menuconfig` - Configure build options
- `make clean` - Clean build artifacts

**Configuration Targets**:
- `make linux-menuconfig` - Configure Linux kernel
- `make uboot-menuconfig` - Configure U-Boot
- `make buildroot-menuconfig` - Configure Buildroot packages

### SDK Directory Structure

```
k230_sdk/
├── configs/           # Board configuration files (defconfig)
├── src/
│   ├── big/          # Big core (RT-Smart) code
│   │   ├── mpp/      # Media Processing Platform
│   │   ├── rt-smart/ # RT-Smart RTOS kernel
│   │   └── ai/       # AI models and runtime
│   ├── little/       # Small core (Linux) code
│   │   ├── linux/    # Linux kernel
│   │   ├── uboot/    # U-Boot bootloader
│   │   └── buildroot-ext/  # Buildroot configuration
│   └── common/       # Shared code (CDK - Communication Development Kit)
├── board/            # Board-specific configurations
├── tools/            # Build tools, Docker, scripts
└── output/           # Build outputs (images)
```

### SDK Build Output

After successful build, images are in `output/<config>/images/`:
- `sysimage-sdcard.img` - SD card image (flash with `dd` or rufus)
- `sysimage-spinor32m.img` - NOR flash image

### Flashing SDK Images

```bash
# Linux
sudo dd if=sysimage-sdcard.img of=/dev/sdX bs=1M oflag=sync

# Windows: Use rufus (rufus.ie)
```

## Reference Links

- Board Documentation: www.lckfb.com
- CanMV K230 API Docs: https://developer.canaan-creative.com/k230_canmv
- MicroPython Docs: https://docs.micropython.org
- Community Forum: www.jlc-bbs.com/lckfb
- K230 SDK GitHub: https://github.com/kendryte/k230_sdk
- K230 Documentation: https://github.com/kendryte/k230_docs
- Canaan Developer Portal: https://developer.canaan-creative.com/

## Board-Specific Quirks

- No backup RTC battery - time resets on power loss (use NTP via WiFi or external RTC like SD3078)
- Buzzer optimized for 4kHz resonance frequency
- LCD backlight uses PWM5 with current-limiting resistor (111mA default)
- GH1.25 connectors have locking mechanism - press tab before pulling
- 40-pin header is Raspberry Pi compatible but lacks ADC (by design for safety)
- Boot pins (GPIO0/1) have drive strength limit - don't set to max
- Default GC2093 camera fixed focus at 70cm - purchase large lens version for manual focus or carefully break adhesive to adjust
- Camera ISP (Image Signal Processor) auto-adjusts exposure/white balance - cannot manually control in current firmware
- K230 sensor architecture: 3 sensor inputs (CSI0/1/2) → 3 camera devices → 3 output channels each
- Each camera sensor can output 3 simultaneous streams at different resolutions/formats
- Touch screen polling-only (no interrupt/callback system in current firmware)
- Touch coordinates may need calibration depending on LCD rotation setting
- Video encoder binds directly to sensor channel - no manual frame feeding
- Audio playback blocking operation - use threads for background audio
- WiFi and Ethernet cannot be used simultaneously (firmware limitation)
- WiFi AP mode and STA mode share same WLAN interface - disconnect one before using other
- Network socket API standard MicroPython - compatible with most socket libraries
- USB-to-Ethernet must use specific RTL8152B chipset (RTL8153 not supported)
- AI models (kmodel) stored in /sdcard/examples/kmodel/ directory
- Face database features stored in /sdcard/examples/utils/db/ as .bin files
- PipeLine creates dual video streams automatically (display + inference)
- Ai2d preprocessing runs on dedicated hardware accelerator (not CPU)
- KPU (Knowledge Processing Unit) is the NPU for neural network inference
- Face detection uses anchor-based detection (YOLO-style)
- Face recognition features are 128-dimensional normalized vectors
- Multiple AI tasks can share same PipeLine instance
- OSD overlay drawing more efficient than modifying original frame
- Image alignment width must be 16-byte aligned for optimal performance
- ulab.numpy provides subset of numpy functionality (not all operations supported)

## Common Image Processing Workflows

**Basic Camera Preview**:
1. Create Sensor object with ID (0, 1, or 2 for CSI port)
2. Call `sensor.reset()`
3. Configure resolution and pixel format
4. Initialize Display and MediaManager
5. Call `sensor.run()`
6. Loop: `sensor.snapshot()` → process → `Display.show_image()`

**Color-Based Object Tracking**:
1. Use IDE Threshold Editor to find LAB color ranges
2. Set sensor to RGB565 format
3. Call `img.find_blobs(thresholds, area_threshold=X)`
4. Filter blobs by area, pixels, or custom callback
5. Draw rectangles/crosses on detected blobs

**Barcode/QR Scanning**:
1. Set sensor to GRAYSCALE format (critical for accuracy)
2. Use moderate resolution (640x480 or 800x480)
3. Ensure proper focus distance (~70cm for default lens)
4. Call `img.find_barcodes()` or `img.find_qrcodes()`
5. Parse `code.payload()` for data

**AprilTag Localization**:
1. Set sensor to GRAYSCALE format
2. Generate tags using IDE tool (Tools → Machine Vision → AprilTag Generator)
3. Choose tag family (TAG36H11 recommended - 587 unique IDs)
4. Call `img.find_apriltags(families=image.TAG36H11)`
5. Use `tag.id()`, `tag.cx()`, `tag.cy()`, `tag.rotation()` for positioning

**Saving Images to SD Card**:
1. Capture image with `sensor.snapshot()`
2. Compress with `compressed = img.compress(quality=95)`
3. Write to file: `open(filename, 'wb').write(compressed)`
4. Images saved as JPEG regardless of capture format

**Interactive Touch Display**:
1. Initialize LCD with touch screen support
2. Initialize TOUCH driver with correct rotation
3. Main loop: read touch data, check event type
4. Draw UI elements on image before `Display.show_image()`
5. Handle touch coordinates to trigger actions

**Recording Video with Audio**:
1. Initialize sensor and audio input (AI)
2. Create video encoder (H264/H265) and bind to sensor channel
3. Create audio encoder and bind to audio input
4. Open MP4 file and bind both encoders
5. Start recording (automatic frame/audio processing)
6. Stop encoders and close file (automatically muxes audio+video)

**WiFi Data Logging**:
1. Connect to WiFi network (STA mode)
2. Use socket or urequests to send data to server
3. For NTP time sync: `import ntptime; ntptime.settime()`
4. Reconnect logic: check `wlan.isconnected()` periodically
5. Handle network errors with try/except

**AI Model Inference (Face Detection Example)**:
1. Initialize PipeLine for dual video streams (display + AI processing)
2. Load kmodel with AIBase subclass
3. Configure AI2D preprocessing (pad, resize, affine, crop)
4. Main loop: get frame → preprocess → inference → postprocess → draw results
5. Use aidemo library for common post-processing tasks
6. Cleanup: call deinit() on AI instances and pl.destroy()

## AI Framework API Reference

### nncase_runtime Module

The `nncase_runtime` module provides low-level KPU (Neural Processing Unit) access for running kmodel inference and AI2D hardware preprocessing.

**Key Classes**:
- `nn.kpu()`: KPU instance for running neural network inference
- `nn.ai2d()`: Hardware-accelerated image preprocessing
- `nn.from_numpy()`: Convert ulab.numpy array to runtime_tensor
- `runtime_tensor.to_numpy()`: Convert runtime_tensor to ulab.numpy array

**KPU Methods**:
```python
import nncase_runtime as nn

# Load kmodel
kpu = nn.kpu()
kpu.load_kmodel("/sdcard/examples/kmodel/face_detection_320.kmodel")

# Set input tensor
input_tensor = nn.from_numpy(img_chw)
kpu.set_input_tensor(0, input_tensor)

# Run inference
kpu.run()

# Get outputs
for i in range(kpu.outputs_size()):
    output = kpu.get_output_tensor(i)
    result = output.to_numpy()

# Query model info
input_count = kpu.inputs_size()
output_count = kpu.outputs_size()
input_desc = kpu.get_input_desc(0)  # Returns dtype, start, size
output_desc = kpu.get_output_desc(0)
```

**AI2D Low-Level Methods**:
```python
# Build AI2D preprocessor
ai2d = nn.ai2d()
ai2d.set_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
               np.uint8, np.uint8)
ai2d.set_resize_param(True, nn.interp_method.tf_bilinear,
                      nn.interp_mode.half_pixel)
ai2d_builder = ai2d.build([1,3,1080,1920], [1,3,320,320])

# Run preprocessing
input_tensor = nn.from_numpy(img_chw)
output_tensor = nn.from_numpy(output_data)
ai2d_builder.run(input_tensor, output_tensor)
```

**Data Format Constants**:
```python
# AI2D formats
nn.ai2d_format.YUV420_NV12      # Input: NV12
nn.ai2d_format.YUV420_NV21      # Input: NV21
nn.ai2d_format.RGB_packed       # Input: RGB packed (HWC)
nn.ai2d_format.NCHW_FMT         # NCHW format (CHW)

# Interpolation methods
nn.interp_method.tf_nearest     # TensorFlow nearest neighbor
nn.interp_method.tf_bilinear    # TensorFlow bilinear
nn.interp_method.cv2_nearest    # OpenCV nearest neighbor
nn.interp_method.cv2_bilinear   # OpenCV bilinear

# Interpolation modes
nn.interp_mode.none             # No alignment
nn.interp_mode.align_corner     # Corner alignment
nn.interp_mode.half_pixel       # Half-pixel alignment

# Data types
np.uint8, np.float
```

**Complete nncase_runtime Example**:
```python
import nncase_runtime as nn
import ulab.numpy as np
import image

# Load kmodel
kmodel_path = "/sdcard/examples/kmodel/face_detection_320.kmodel"
kpu = nn.kpu()
kpu.load_kmodel(kmodel_path)

# Read and convert image to CHW format
img_path = "/sdcard/examples/utils/db_img/id_1.jpg"
img_data = image.Image(img_path).to_rgb888()
img_hwc = img_data.to_numpy_ref()
shape = img_hwc.shape
img_tmp = img_hwc.reshape((shape[0] * shape[1], shape[2]))
img_tmp_trans = img_tmp.transpose().copy()
img_chw = img_tmp_trans.reshape((shape[2], shape[0], shape[1]))

# AI2D preprocessing to 320x320
ai2d = nn.ai2d()
output_data = np.ones((1,3,320,320), dtype=np.uint8)
ai2d_output_tensor = nn.from_numpy(output_data)
ai2d.set_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
               np.uint8, np.uint8)
ai2d.set_resize_param(True, nn.interp_method.tf_bilinear,
                      nn.interp_mode.half_pixel)
ai2d_builder = ai2d.build([1,3,img_chw.shape[1],img_chw.shape[2]],
                          [1,3,320,320])
ai2d_input_tensor = nn.from_numpy(img_chw)
ai2d_builder.run(ai2d_input_tensor, ai2d_output_tensor)

# KPU inference
kpu.set_input_tensor(0, ai2d_output_tensor)
kpu.run()

# Get outputs
for i in range(kpu.outputs_size()):
    output_data = kpu.get_output_tensor(i)
    result = output_data.to_numpy()
    print(result.shape)
```

### PipeLine Module

The `PipeLine` class from `libs.PipeLine` manages dual video streams for AI applications.

**Constructor**:
```python
from libs.PipeLine import PipeLine, ScopedTiming

pl = PipeLine(rgb888p_size=[1920,1080],    # AI input resolution
              display_size=[1920,1080],     # Display resolution
              display_mode='hdmi',          # 'hdmi' or 'lcd'
              debug_mode=0)                 # 0=timing, 1=no timing
```

**Methods**:
```python
# Initialize media pipeline
pl.create(sensor=None,      # Optional: custom Sensor instance
          hmirror=None,     # Optional: horizontal mirror (True/False)
          vflip=None,       # Optional: vertical flip (True/False)
          fps=60)           # Sensor frame rate

# Get frame for AI processing (returns ulab.numpy.ndarray in CHW format)
img = pl.get_frame()

# Display AI results drawn on pl.osd_img
pl.show_image()

# Cleanup
pl.destroy()
```

**OSD (On-Screen Display) Layer**:
```python
# pl.osd_img is an image.ARGB8888 image for drawing results
pl.osd_img.clear()  # Clear previous drawings
pl.osd_img.draw_rectangle(x, y, w, h, color=(255,255,0,255), thickness=2)
pl.osd_img.draw_circle(x, y, r, color=(0,255,0,255), thickness=2)
pl.osd_img.draw_string_advanced(x, y, size, "文字", color=(255,0,0,255))
```

**ScopedTiming Context Manager**:
```python
# Automatic timing for performance profiling
with ScopedTiming("preprocessing", debug_mode=1):
    # Code block to time
    result = ai2d.run(img)
# Prints execution time when exiting context
```

**Complete PipeLine Example**:
```python
from libs.PipeLine import PipeLine, ScopedTiming
from media.media import *
import gc
import sys, os

if __name__ == "__main__":
    display_mode = "hdmi"
    if display_mode == "hdmi":
        display_size = [1920, 1080]
    else:
        display_size = [800, 480]

    # Initialize PipeLine
    pl = PipeLine(rgb888p_size=[1920,1080],
                  display_size=display_size,
                  display_mode=display_mode)
    pl.create()

    try:
        while True:
            os.exitpoint()
            with ScopedTiming("total", 1):
                img = pl.get_frame()
                print(img.shape)  # (3, 1080, 1920) - CHW format
                gc.collect()
    except Exception as e:
        sys.print_exception(e)
    finally:
        pl.destroy()
```

### Ai2d Module

The `Ai2d` class from `libs.AI2D` provides high-level preprocessing configuration.

**Constructor**:
```python
from libs.AI2D import Ai2d
import nncase_runtime as nn
import ulab.numpy as np

ai2d = Ai2d(debug_mode=0)
```

**Configuration Methods**:
```python
# Set data types (required before any operations)
ai2d.set_ai2d_dtype(input_format=nn.ai2d_format.NCHW_FMT,
                    output_format=nn.ai2d_format.NCHW_FMT,
                    input_type=np.uint8,
                    output_type=np.uint8)

# Crop operation
ai2d.crop(start_x, start_y, width, height)

# Shift operation (right shift for normalization)
ai2d.shift(shift_val=2)  # Right shift by 2 bits

# Padding operation
# Format: [r_pad, g_pad, b_pad, a_pad, top, bottom, left, right]
ai2d.pad(paddings=[0,0,0,0,5,5,15,15],
         pad_mode=0,  # Always 0 (constant padding)
         pad_val=[114,114,114])  # RGB padding values

# Resize operation
ai2d.resize(interp_method=nn.interp_method.tf_bilinear,
            interp_mode=nn.interp_mode.half_pixel)

# Affine transformation
affine_matrix = [0.2159457, -0.031286, -59.5312,
                 0.031286, 0.2159457, -35.30719]  # 2x3 matrix flattened
ai2d.affine(interp_method=nn.interp_method.cv2_bilinear,
            cord_round=0,        # Coordinate rounding
            bound_ind=0,         # Boundary mode
            bound_val=127,       # Boundary fill value
            bound_smooth=1,      # Boundary smoothing
            M=affine_matrix)     # Transformation matrix

# Build preprocessing pipeline
ai2d.build(ai2d_input_shape=[1,3,512,512],
           ai2d_output_shape=[1,3,640,640])

# Run preprocessing (returns nn.runtime_tensor)
output_tensor = ai2d.run(input_np)
```

**Important Ai2d Notes**:
```
(1) Affine and Resize are mutually exclusive - cannot use both
(2) Shift operation only works with Raw16 input format
(3) Pad values must match channel count (RGB = 3 values)
(4) Operation order: Crop → Shift → Resize/Affine → Pad
(5) For different order, create multiple Ai2d instances
```

**Input/Output Format Compatibility**:
```
Input Format     → Output Format        Notes
YUV420_NV12      → RGB_planar/NV12
YUV420_NV21      → RGB_planar/NV21
YUV420_I420      → RGB_planar/I420
YUV400           → YUV400
NCHW(RGB_planar) → NCHW(RGB_planar)
RGB_packed       → RGB_planar/RGB_packed
RAW16            → RAW16/8              Depth maps, use with shift
```

**Complete Ai2d Example**:
```python
from libs.PipeLine import PipeLine, ScopedTiming
from libs.AI2D import Ai2d
import nncase_runtime as nn
import gc, sys, os

if __name__ == "__main__":
    display_mode = "hdmi"
    display_size = [1920,1080] if display_mode=="hdmi" else [800,480]

    pl = PipeLine(rgb888p_size=[512,512],
                  display_size=display_size,
                  display_mode=display_mode)
    pl.create()

    # Configure resize preprocessing
    my_ai2d = Ai2d(debug_mode=0)
    my_ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,
                           nn.ai2d_format.NCHW_FMT,
                           np.uint8, np.uint8)
    my_ai2d.resize(nn.interp_method.tf_bilinear,
                   nn.interp_mode.half_pixel)
    my_ai2d.build([1,3,512,512], [1,3,640,640])

    try:
        while True:
            os.exitpoint()
            with ScopedTiming("total", 1):
                img = pl.get_frame()
                print(img.shape)  # [3,512,512]
                ai2d_output_tensor = my_ai2d.run(img)
                ai2d_output_np = ai2d_output_tensor.to_numpy()
                print(ai2d_output_np.shape)  # [1,3,640,640]
                gc.collect()
    except Exception as e:
        sys.print_exception(e)
    finally:
        pl.destroy()
```

### AIBase Module

The `AIBase` class from `libs.AIBase` provides base functionality for AI applications.

**Constructor**:
```python
from libs.AIBase import AIBase

# Typically used as parent class, not directly instantiated
aibase = AIBase(kmodel_path="**.kmodel",
                model_input_size=[224,224],
                rgb888p_size=[1280,720],
                debug_mode=0)
```

**Methods to Override in Subclass**:
```python
class MyAIApp(AIBase):
    def __init__(self, kmodel_path, model_input_size, rgb888p_size=[1920,1080],
                 display_size=[1920,1080], debug_mode=0):
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,
                                  nn.ai2d_format.NCHW_FMT,
                                  np.uint8, np.uint8)

    # Configure Ai2d preprocessing (must implement)
    def config_preprocess(self, input_image_size=None):
        ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
        # Configure ai2d operations
        self.ai2d.resize(nn.interp_method.tf_bilinear,
                        nn.interp_mode.half_pixel)
        self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],
                       [1,3,self.model_input_size[1],self.model_input_size[0]])

    # Post-process model outputs (must implement)
    def postprocess(self, results):
        # results is list of ulab.numpy.ndarray from model outputs
        return processed_results

    # Draw results on display (must implement)
    def draw_result(self, pl, results):
        pl.osd_img.draw_rectangle(x, y, w, h,
                                  color=(255,255,0,255), thickness=2)
```

**AIBase Methods**:
```python
# Query model info
input_count = aibase.get_kmodel_inputs_num()
output_count = aibase.get_kmodel_outputs_num()

# Preprocess (calls ai2d configured in config_preprocess)
input_tensors = aibase.preprocess(input_np)

# Inference (runs kmodel and returns list of numpy arrays)
results = aibase.inference()

# Run complete pipeline (preprocess → inference → postprocess)
results = aibase.run(input_np)

# Cleanup
aibase.deinit()
```

**Data Type Conversion Utilities**:
```python
# Image to numpy (HWC format)
import image
img_hwc = image.Image(img_path).to_rgb888().to_numpy_ref()

# HWC to CHW conversion
shape = img_hwc.shape
img_tmp = img_hwc.reshape((shape[0] * shape[1], shape[2]))
img_tmp_trans = img_tmp.transpose().copy()
img_chw = img_tmp_trans.reshape((shape[2], shape[0], shape[1]))

# Numpy to Image (ARGB8888)
import ulab.numpy as np
img_np = np.zeros((height, width, 4), dtype=np.uint8)
img = image.Image(width, height, image.ARGB8888,
                 alloc=image.ALLOC_REF, data=img_np)

# Numpy to tensor
tensor = nn.from_numpy(img_np)

# Tensor to numpy
img_np = tensor.to_numpy()
```

### YOLO Module

The `YOLO` module from `libs.YOLO` provides pre-built support for YOLOv5, YOLOv8, and YOLO11 models.

**Supported Tasks**:
- **classify**: Image classification
- **detect**: Object detection
- **segment**: Instance segmentation

**YOLOv5 Class**:
```python
from libs.YOLO import YOLOv5

yolo = YOLOv5(
    task_type="detect",           # 'classify', 'detect', or 'segment'
    mode="video",                 # 'image' or 'video'
    kmodel_path="/path/to/model.kmodel",
    labels=["apple", "banana", "orange"],
    rgb888p_size=[1280,720],      # Input frame size
    model_input_size=[320,320],   # Model training input size
    display_size=[1920,1080],     # Display resolution (video mode only)
    conf_thresh=0.5,              # Confidence threshold
    nms_thresh=0.25,              # NMS threshold (detect/segment only)
    mask_thresh=0.5,              # Mask threshold (segment only)
    max_boxes_num=50,             # Max detections per frame
    debug_mode=0)

# Configure preprocessing
yolo.config_preprocess()

# Run inference (image mode)
img_chw = read_img(img_path)  # CHW format
results = yolo.run(img_chw)
yolo.draw_result(results, img_ori)

# Run inference (video mode with PipeLine)
pl = PipeLine(rgb888p_size=[1280,720], display_size=[1920,1080],
              display_mode="hdmi")
pl.create()

while True:
    img = pl.get_frame()
    results = yolo.run(img)
    yolo.draw_result(results, pl.osd_img)
    pl.show_image()

# Cleanup
yolo.deinit()
pl.destroy()
```

**YOLOv8 Class** (same API as YOLOv5):
```python
from libs.YOLO import YOLOv8

yolo = YOLOv8(task_type="classify", mode="video", ...)
# Same methods as YOLOv5
```

**YOLO11 Class** (same API as YOLOv5):
```python
from libs.YOLO import YOLO11

yolo = YOLO11(task_type="segment", mode="image", ...)
# Same methods as YOLOv5
```

**YOLO Return Values**:
```python
# Classification task
class_index, confidence = yolo.run(img)

# Detection task
detections = yolo.run(img)  # List of [x, y, w, h, confidence, class_index]

# Segmentation task
masks, detections = yolo.run(img)
# masks: Binary segmentation masks
# detections: List of [x, y, w, h, confidence, class_index]
```

**Complete YOLO Detection Example**:
```python
from libs.PipeLine import PipeLine, ScopedTiming
from libs.YOLO import YOLOv5
import os, sys, gc

if __name__ == "__main__":
    display_mode = "hdmi"
    rgb888p_size = [1280, 720]
    display_size = [1920, 1080] if display_mode=="hdmi" else [800, 480]

    kmodel_path = "/sdcard/examples/kmodel/det_yolov5n_320.kmodel"
    labels = ["apple", "banana", "orange"]

    # Initialize PipeLine
    pl = PipeLine(rgb888p_size=rgb888p_size,
                  display_size=display_size,
                  display_mode=display_mode)
    pl.create()

    # Initialize YOLOv5
    yolo = YOLOv5(task_type="detect", mode="video",
                  kmodel_path=kmodel_path, labels=labels,
                  rgb888p_size=rgb888p_size,
                  model_input_size=[320,320],
                  display_size=display_size,
                  conf_thresh=0.8, nms_thresh=0.45,
                  max_boxes_num=50, debug_mode=0)
    yolo.config_preprocess()

    try:
        while True:
            os.exitpoint()
            with ScopedTiming("total", 1):
                img = pl.get_frame()
                detections = yolo.run(img)
                yolo.draw_result(detections, pl.osd_img)
                pl.show_image()
                gc.collect()
    except Exception as e:
        sys.print_exception(e)
    finally:
        yolo.deinit()
        pl.destroy()
```

**YOLO Model Deployment Tips**:
- Train models using official YOLOv5/YOLOv8/YOLO11 repositories
- Convert to ONNX format first
- Use nncase toolkit to convert ONNX to kmodel format
- Model input size must be square (e.g., 224x224, 320x320, 640x640)
- Larger input sizes increase accuracy but reduce FPS
- Adjust confidence threshold to balance false positives/negatives
- NMS threshold controls overlapping box suppression (lower = fewer boxes)

## Desktop Pet Project (Current Focus)

This repository contains a desktop pet project built on the K230 CanMV platform.

### Quick Start

**Deploy to board:**
```bash
# Copy src/ contents to /sdcard/pet/ on the K230 SD card
# Required model files (should already exist):
#   /sdcard/examples/kmodel/face_detection_320.kmodel
#   /sdcard/examples/kmodel/face_pose.kmodel
#   /sdcard/examples/utils/prior_data_320.bin
```

**Run the desktop pet:**
```python
# From CanMV IDE or serial console:
import sys
sys.path.append('/sdcard/pet')
exec(open('/sdcard/pet/main.py').read())
```

**Test individual modules:**
```python
# Test LCD display only (no AI):
exec(open('/sdcard/pet/test_lcd_simple.py').read())

# Test face pose detection:
exec(open('/sdcard/pet/vision/face_pose_test.py').read())
```

### State Machine

```
                    ┌──────────────────┐
                    │      IDLE        │
                    │  (sleepy face)   │
                    │  waiting for     │
                    │  user attention  │
                    └────────┬─────────┘
                             │
                             │ yaw < 20° (user looking at pet)
                             ▼
                    ┌──────────────────┐
                    │     ACTIVE       │◀─────┐
                    │  (happy/curious) │      │
                    │  eyes track user │      │ face detected
                    │  animations on   │──────┘
                    └────────┬─────────┘
                             │
                             │ yaw > 35° for 3+ seconds
                             │ (user turns away)
                             ▼
                    ┌──────────────────┐
                    │  Back to IDLE    │
                    └──────────────────┘
```

### Development Progress

| Step | Feature | Status | Notes |
|------|---------|--------|-------|
| 1 | Display System | ✅ Complete | 25-30 FPS with C-accelerated rendering |
| 2 | Head Detection | ✅ Complete | Face detection + yaw/pitch/roll estimation |
| 3 | Visual Linkage | ✅ Complete | Eye tracking + state machine + blink/breath animations |
| 4 | Network/WiFi | ⬜ Pending | Cloud WebSocket integration |
| 5 | Audio System | ⬜ Pending | Microphone recording + TTS playback |
| 6 | Full Integration | ⬜ Pending | Complete interactive workflow |

### Key Configuration (src/main.py)

```python
WAKE_YAW_THRESHOLD = 20        # Wake when |yaw| < 20°
EXIT_YAW_THRESHOLD = 35        # Start exit countdown when |yaw| > 35°
EXIT_TIMEOUT_FRAMES = 90       # ~3 seconds at 30 FPS before exit
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
```

### Project Structure

```
src/                               # Deploy to /sdcard/pet/
├── main.py                        # Main entry: state machine + AI + rendering
├── config.py                      # Configuration parameters
├── test_lcd_simple.py             # LCD test without AI
├── display/
│   ├── __init__.py
│   └── pet_face.py                # High-performance animated face (C-accelerated)
└── vision/
    ├── __init__.py
    ├── head_pose.py               # Head pose detection classes
    └── face_pose_test.py          # Standalone pose detection test
```

### Key Implementation Details

**PetFace class** (`src/main.py:32-246`):
- Uses `image.ARGB8888` with transparent background for overlay
- Draws using C-accelerated `draw_circle()`, `draw_ellipse()` - NOT Python loops
- Implements blink animation (random interval 2.5-5s)
- Implements breathing animation (sinusoidal y-offset)
- Smooth pupil movement with lerp interpolation

**FaceDetApp class** (`src/main.py:248-293`):
- Wraps face detection kmodel (320×320 input)
- Uses aidemo.face_det_post_process() for NMS

**FacePoseApp class** (`src/main.py:295-346`):
- Wraps head pose kmodel (120×120 input)
- Extracts rotation matrix → Euler angles (pitch, yaw, roll)

### Related Documentation

- `/K230_GRAPHICS_OPTIMIZATION.md`: Critical performance guide - why Python loops fail
- `/docs/architecture.md`: System architecture and cloud integration design
- `/docs/development_plan.md`: Detailed task breakdown and progress log

## FOC Motor Control (Reference Documentation)

The `/foc/` directory contains reference documentation and archived source code for FOC (Field Oriented Control) motor control. This is reference material for future K230 FOC implementation.

**Hardware for FOC projects**:
- BLDC motor with AS5600 magnetic encoder (12-bit, I2C address 0x36)
- 3-phase PWM driver (DRV8313 or similar)
- Power supply (12V typical)

**Recommended Pin Configuration**:
| Function | Motor 1 | Motor 2 |
|----------|---------|---------|
| PWM U | PWM0 | PWM3 |
| PWM V | PWM1 | PWM4 |
| PWM W | PWM2 | PWM5 |
| Encoder I2C | I2C0 (GPIO48/49) | I2C1 (GPIO40/41) |

**FOC Algorithm Overview**:
```
1. Read encoder angle (electrical angle = mechanical × pole_pairs)
2. Clark Transform: (a,b,c) → (α,β)
3. Park Transform: (α,β) → (d,q) using electrical angle
4. PID control on d,q currents
5. Inverse Park: (d,q) → (α,β)
6. SVPWM: (α,β) → 3-phase PWM duty cycles
```

**Reference Materials in `/foc/`**:
- `说明书/测试说明/`: Test documentation and reference code
- `代码开源/`: Archived SimpleFOC implementations (ESP32, STM32, Arduino)
- `3D模型与尺寸图纸/`: Mechanical drawings and 3D models
