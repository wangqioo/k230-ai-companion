try:
    from .vision_protocol import (
        MSG_ERROR,
        MSG_FACE,
        MSG_FACE_LOST,
        MSG_HEARTBEAT,
        encode_frame,
        pack_face_observation,
    )
except ImportError:
    from vision_protocol import (
        MSG_ERROR,
        MSG_FACE,
        MSG_FACE_LOST,
        MSG_HEARTBEAT,
        encode_frame,
        pack_face_observation,
    )


class VisionPublisher:
    def __init__(self, uart, initial_sequence=0):
        self.uart = uart
        self.sequence = initial_sequence & 0xFFFF

    def _publish(self, message_type, payload, timestamp_ms):
        frame = encode_frame(
            message_type,
            payload,
            sequence=self.sequence,
            timestamp_ms=timestamp_ms,
        )
        written = self.uart.write(frame)
        if written is not None and written != len(frame):
            raise OSError("incomplete UART write")
        self.sequence = (self.sequence + 1) & 0xFFFF
        return len(frame)

    def publish_heartbeat(self, timestamp_ms):
        return self._publish(MSG_HEARTBEAT, b"", timestamp_ms)

    def publish_face_lost(self, timestamp_ms):
        return self._publish(MSG_FACE_LOST, b"", timestamp_ms)

    def publish_error(self, code, timestamp_ms):
        payload = bytes(((code >> 8) & 0xFF, code & 0xFF))
        return self._publish(MSG_ERROR, payload, timestamp_ms)

    def publish_face_observation(self, observation, timestamp_ms):
        payload = pack_face_observation(observation)
        return self._publish(MSG_FACE, payload, timestamp_ms)

    def publish_face(
        self,
        frame_width,
        frame_height,
        box,
        euler,
        confidence,
        timestamp_ms,
    ):
        payload = pack_face_observation(
            frame_width,
            frame_height,
            box,
            euler,
            confidence,
        )
        return self._publish(MSG_FACE, payload, timestamp_ms)
