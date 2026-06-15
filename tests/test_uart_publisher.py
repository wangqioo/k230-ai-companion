import unittest

from src.transport.uart_publisher import VisionPublisher
from src.transport.vision_protocol import (
    MSG_FACE,
    MSG_FACE_LOST,
    MSG_HEARTBEAT,
    decode_frame,
    unpack_face_observation,
)


class MemoryUART:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)
        return len(data)


class VisionPublisherTest(unittest.TestCase):
    def test_publisher_owns_sequence_and_wraps(self):
        uart = MemoryUART()
        publisher = VisionPublisher(uart, initial_sequence=0xFFFF)

        publisher.publish_heartbeat(timestamp_ms=10)
        publisher.publish_face_lost(timestamp_ms=20)

        first = decode_frame(uart.writes[0])
        second = decode_frame(uart.writes[1])
        self.assertEqual(first["type"], MSG_HEARTBEAT)
        self.assertEqual(first["sequence"], 0xFFFF)
        self.assertEqual(second["type"], MSG_FACE_LOST)
        self.assertEqual(second["sequence"], 0)

    def test_publish_face_writes_normalized_observation(self):
        uart = MemoryUART()
        publisher = VisionPublisher(uart)

        publisher.publish_face(
            frame_width=800,
            frame_height=480,
            box=[200, 120, 400, 240],
            euler=[0, 10.5, 0],
            confidence=75,
            timestamp_ms=30,
        )

        frame = decode_frame(uart.writes[0])
        observation = unpack_face_observation(frame["payload"])
        self.assertEqual(frame["type"], MSG_FACE)
        self.assertEqual(observation["center_x"], 0)
        self.assertEqual(observation["yaw_cd"], 1050)
        self.assertEqual(observation["confidence"], 75)

    def test_publish_face_observation_writes_canonical_payload(self):
        uart = MemoryUART()
        publisher = VisionPublisher(uart)

        publisher.publish_face_observation(
            {
                "center_x": -100,
                "center_y": 200,
                "width": 300,
                "height": 400,
                "pitch_cd": 123,
                "yaw_cd": -456,
                "roll_cd": 789,
                "confidence": 88,
            },
            timestamp_ms=40,
        )

        frame = decode_frame(uart.writes[0])
        observation = unpack_face_observation(frame["payload"])
        self.assertEqual(frame["type"], MSG_FACE)
        self.assertEqual(frame["timestamp_ms"], 40)
        self.assertEqual(observation["center_x"], -100)
        self.assertEqual(observation["center_y"], 200)
        self.assertEqual(observation["yaw_cd"], -456)
        self.assertEqual(observation["confidence"], 88)


if __name__ == "__main__":
    unittest.main()
