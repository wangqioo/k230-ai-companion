# K230 Vision Coprocessor Design

## Goal

Make the K230 a dedicated visual coprocessor. The ESP32 owns the product state
machine, real-time control, networking, audio, display, watchdog, and recovery.

## Responsibilities

### K230

- Capture camera frames.
- Run face detection and head-pose inference.
- Select the primary face.
- Publish normalized visual observations over UART2.
- Publish heartbeat and face-lost events.
- Recover locally from inference errors without controlling the product.

### ESP32

- Parse and validate K230 messages.
- Reject corrupt, duplicate, and stale data.
- Convert observations into product behavior.
- Enter a safe no-vision state when messages time out.
- Own every actuator and user-facing state transition.

## Transport

UART2 uses GPIO11 TX and GPIO12 RX at 921600 baud. The first implementation is
one-way from K230 to ESP32, while retaining the RX pin for future commands.

Each frame contains:

| Field | Size | Encoding |
|---|---:|---|
| Magic | 2 | `A5 5A` |
| Version | 1 | `1` |
| Message type | 1 | heartbeat, face, face-lost, error |
| Sequence | 2 | unsigned, big-endian |
| Timestamp | 4 | milliseconds, unsigned, big-endian |
| Payload length | 2 | unsigned, big-endian |
| Payload | variable | message-specific |
| CRC16 | 2 | CRC-16/CCITT-FALSE over header and payload |

Face coordinates are normalized integers so the ESP32 does not depend on the
camera resolution:

- Center X/Y: `-1000..1000`
- Width/height: `0..1000`
- Pitch/yaw/roll: signed centidegrees
- Confidence: `0..100`

## Runtime Flow

1. K230 initializes UART and the visual inference pipeline.
2. Every processed frame produces either a face observation or face-lost state.
3. Repeated face-lost frames are rate-limited.
4. A heartbeat is published once per second even when no face exists.
5. ESP32 incrementally parses UART bytes and validates CRC/version/length.
6. ESP32 marks vision unavailable if no valid frame arrives within 500 ms.

## Failure Handling

- A K230 inference exception publishes an error event when possible, cleans up,
  and allows its watchdog or supervisor to restart it.
- ESP32 never waits synchronously for K230.
- Corrupt frames are discarded and parsing resumes at the next magic sequence.
- Unknown message types are ignored after their frame is validated.
- Sequence wraparound is valid.

## Testing

- Python tests cover encoding, CRC, normalization, sequence wraparound, and
  stream parsing.
- A host-compiled C++ test feeds Python-compatible golden frames through the
  ESP32 parser.
- K230 hardware verification checks UART electrical wiring and real inference.
- ESP32 hardware verification checks the 500 ms no-vision fallback.

## Migration

`src/main_vision_uart.py` becomes the primary K230 entry. Existing
`main_voice.py`, PC gateway code, and media experiments remain temporarily as
legacy references and are not part of the runtime architecture.
