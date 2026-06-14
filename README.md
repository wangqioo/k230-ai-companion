# K230 + ESP32 AI Companion

桌面伙伴采用双芯片分工：

- **K230：视觉协处理器**，只负责摄像头、KPU推理和视觉结果输出。
- **ESP32：系统主控**，负责实时状态机、执行器、音频、屏幕、网络和故障恢复。

K230 的 Python 代码不承担严格实时控制。ESP32 不接收原始图像，只接收经过
K230 处理后的结构化视觉事件。

## Runtime Architecture

```text
GC2093 camera
      |
      v
K230 CanMV
  face detection
  head pose
  primary-face selection
      |
      | UART2 binary frames
      v
ESP32
  CRC + timeout
  real-time state machine
  audio / display / motors / network
```

## Wiring

| K230 | ESP32 | Note |
|---|---|---|
| GPIO11 / UART2 TX | GPIO16 / UART2 RX | Visual events |
| GPIO12 / UART2 RX | GPIO17 / UART2 TX | Reserved for future commands |
| GND | GND | Required common ground |

Both boards use 3.3V logic. Default baud rate is `921600`, format `8N1`.

## K230 Deployment

Copy `src/` to `/sdcard/pet/`, then run:

```python
import sys
sys.path.append("/sdcard/pet")
exec(open("/sdcard/pet/main_vision_uart.py").read())
```

Required model files:

```text
/sdcard/examples/kmodel/face_detection_320.kmodel
/sdcard/examples/kmodel/face_pose.kmodel
/sdcard/examples/utils/prior_data_320.bin
```

The primary entry is [src/main_vision_uart.py](src/main_vision_uart.py).

## ESP32 Deployment

Open [esp32/vision_receiver/vision_receiver.ino](esp32/vision_receiver/vision_receiver.ino)
with Arduino IDE or incorporate `vision_protocol.h/.cpp` into the ESP32 firmware.

The example:

- Incrementally parses UART bytes.
- Rejects invalid CRC frames.
- Tracks face and face-lost events.
- Enters a no-vision state after 500 ms without a valid frame.

Product behavior belongs in the marked ESP32 state-machine hooks.

## UART Protocol

```text
Magic(2) Version(1) Type(1) Sequence(2) Timestamp(4)
PayloadLength(2) Payload(N) CRC16(2)
```

- Integers are big-endian.
- CRC is CRC-16/CCITT-FALSE.
- Face coordinates are normalized and independent of camera resolution.
- Full details are in
  [the design document](docs/superpowers/specs/2026-06-14-k230-vision-coprocessor-design.md).

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v

g++ -std=c++17 -Wall -Wextra -pedantic \
  tests/cpp/test_vision_protocol.cpp \
  esp32/vision_receiver/vision_protocol.cpp \
  -o /tmp/test_vision_protocol
/tmp/test_vision_protocol
```

## Legacy Experiments

The following files are retained as references but are no longer the target
runtime architecture:

- `src/main.py`: K230 visual display experiment.
- `src/main_voice.py`: K230 audio and voice conversation experiment.
- `server/`: PC ASR/LLM/TTS gateway experiment.
- `src/network/`: K230 network and audio probes.

New product behavior should be implemented on ESP32, not added to these K230
experiments.

## Hardware Notes

- K230 UART0 is reserved for the RT-Smart console; use UART2.
- K230/ESP32 GPIO are 3.3V only.
- K230 ADC inputs are limited to 1.8V.
- Call K230 inference and drawing functions provided by the firmware instead of
  pixel-by-pixel Python loops.
