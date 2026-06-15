try:
    import ustruct as struct
except ImportError:
    import struct


MAGIC = b"\xA5\x5A"
VERSION = 1
HEADER_FORMAT = ">2sBBHIH"
HEADER_SIZE = 12
CRC_SIZE = 2
MAX_PAYLOAD_SIZE = 256

MSG_HEARTBEAT = 1
MSG_FACE = 2
MSG_FACE_LOST = 3
MSG_ERROR = 127

FACE_FORMAT = ">hhhhhhhB"
FACE_PAYLOAD_SIZE = 15


def _clamp(value, minimum, maximum):
    return minimum if value < minimum else maximum if value > maximum else value


def crc16_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode_frame(message_type, payload=b"", sequence=0, timestamp_ms=0):
    if payload is None:
        payload = b""
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError("payload too large")

    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        VERSION,
        message_type & 0xFF,
        sequence & 0xFFFF,
        timestamp_ms & 0xFFFFFFFF,
        len(payload),
    )
    body = header + payload
    return body + struct.pack(">H", crc16_ccitt(body))


def decode_frame(frame):
    if len(frame) < HEADER_SIZE + CRC_SIZE:
        raise ValueError("frame too short")

    magic, version, message_type, sequence, timestamp_ms, payload_length = (
        struct.unpack(HEADER_FORMAT, frame[:HEADER_SIZE])
    )
    if magic != MAGIC:
        raise ValueError("invalid magic")
    if version != VERSION:
        raise ValueError("unsupported version")
    if payload_length > MAX_PAYLOAD_SIZE:
        raise ValueError("payload too large")

    expected_size = HEADER_SIZE + payload_length + CRC_SIZE
    if len(frame) != expected_size:
        raise ValueError("invalid frame length")

    expected_crc = struct.unpack(">H", frame[-CRC_SIZE:])[0]
    actual_crc = crc16_ccitt(frame[:-CRC_SIZE])
    if expected_crc != actual_crc:
        raise ValueError("crc mismatch")

    return {
        "type": message_type,
        "sequence": sequence,
        "timestamp_ms": timestamp_ms,
        "payload": frame[HEADER_SIZE:-CRC_SIZE],
    }


CANONICAL_FACE_FIELDS = (
    "center_x",
    "center_y",
    "width",
    "height",
    "pitch_cd",
    "yaw_cd",
    "roll_cd",
    "confidence",
)


def pack_canonical_face_observation(observation):
    missing = [
        field for field in CANONICAL_FACE_FIELDS if field not in observation
    ]
    if missing:
        raise ValueError("missing face observation fields: " + ",".join(missing))

    return struct.pack(
        FACE_FORMAT,
        _clamp(int(observation["center_x"]), -1000, 1000),
        _clamp(int(observation["center_y"]), -1000, 1000),
        _clamp(int(observation["width"]), 0, 1000),
        _clamp(int(observation["height"]), 0, 1000),
        _clamp(int(observation["pitch_cd"]), -32768, 32767),
        _clamp(int(observation["yaw_cd"]), -32768, 32767),
        _clamp(int(observation["roll_cd"]), -32768, 32767),
        _clamp(int(observation["confidence"]), 0, 100),
    )


def pack_face_observation(
    frame_width, frame_height=None, box=None, euler=None, confidence=100
):
    if isinstance(frame_width, dict):
        if frame_height is not None or box is not None or euler is not None:
            raise ValueError("canonical observation cannot be mixed with legacy arguments")
        return pack_canonical_face_observation(frame_width)

    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive")

    x, y, width, height = box[:4]
    pitch, yaw, roll = euler
    center_x = int(round(((x + width / 2) * 2000 / frame_width) - 1000))
    center_y = int(round(((y + height / 2) * 2000 / frame_height) - 1000))
    normalized_width = int(round(width * 1000 / frame_width))
    normalized_height = int(round(height * 1000 / frame_height))
    confidence_percent = (
        int(round(confidence * 100)) if confidence <= 1 else int(round(confidence))
    )

    return struct.pack(
        FACE_FORMAT,
        _clamp(center_x, -1000, 1000),
        _clamp(center_y, -1000, 1000),
        _clamp(normalized_width, 0, 1000),
        _clamp(normalized_height, 0, 1000),
        _clamp(int(round(pitch * 100)), -32768, 32767),
        _clamp(int(round(yaw * 100)), -32768, 32767),
        _clamp(int(round(roll * 100)), -32768, 32767),
        _clamp(confidence_percent, 0, 100),
    )


def unpack_face_observation(payload):
    if len(payload) != FACE_PAYLOAD_SIZE:
        raise ValueError("invalid face payload length")
    values = struct.unpack(FACE_FORMAT, payload)
    return {
        "center_x": values[0],
        "center_y": values[1],
        "width": values[2],
        "height": values[3],
        "pitch_cd": values[4],
        "yaw_cd": values[5],
        "roll_cd": values[6],
        "confidence": values[7],
    }


class StreamDecoder:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        if data:
            self.buffer.extend(data)

        frames = []
        while True:
            magic_index = self.buffer.find(MAGIC)
            if magic_index < 0:
                if self.buffer and self.buffer[-1] == MAGIC[0]:
                    self.buffer[:] = self.buffer[-1:]
                else:
                    self.buffer[:] = b""
                break
            if magic_index:
                del self.buffer[:magic_index]
            if len(self.buffer) < HEADER_SIZE:
                break

            payload_length = struct.unpack(">H", self.buffer[10:12])[0]
            if payload_length > MAX_PAYLOAD_SIZE:
                del self.buffer[0]
                continue

            frame_size = HEADER_SIZE + payload_length + CRC_SIZE
            if len(self.buffer) < frame_size:
                break

            candidate = bytes(self.buffer[:frame_size])
            try:
                frames.append(decode_frame(candidate))
                del self.buffer[:frame_size]
            except ValueError:
                del self.buffer[0]
        return frames
