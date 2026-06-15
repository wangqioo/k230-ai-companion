import unittest

from src.transport.vision_protocol import (
    MSG_FACE,
    MSG_HEARTBEAT,
    StreamDecoder,
    crc16_ccitt,
    decode_frame,
    encode_frame,
    pack_face_observation,
    unpack_face_observation,
)


class VisionProtocolTest(unittest.TestCase):
    def test_crc_matches_ccitt_false_reference(self):
        self.assertEqual(crc16_ccitt(b"123456789"), 0x29B1)

    def test_frame_round_trip(self):
        encoded = encode_frame(MSG_HEARTBEAT, b"", sequence=42, timestamp_ms=1234)

        decoded = decode_frame(encoded)

        self.assertEqual(decoded["type"], MSG_HEARTBEAT)
        self.assertEqual(decoded["sequence"], 42)
        self.assertEqual(decoded["timestamp_ms"], 1234)
        self.assertEqual(decoded["payload"], b"")

    def test_face_observation_is_resolution_independent(self):
        payload = pack_face_observation(
            frame_width=1920,
            frame_height=1080,
            box=[480, 270, 960, 540],
            euler=[12.34, -5.67, 1.25],
            confidence=0.92,
        )

        observation = unpack_face_observation(payload)

        self.assertEqual(observation["center_x"], 0)
        self.assertEqual(observation["center_y"], 0)
        self.assertEqual(observation["width"], 500)
        self.assertEqual(observation["height"], 500)
        self.assertEqual(observation["pitch_cd"], 1234)
        self.assertEqual(observation["yaw_cd"], -567)
        self.assertEqual(observation["roll_cd"], 125)
        self.assertEqual(observation["confidence"], 92)

    def test_pack_canonical_face_observation(self):
        payload = pack_face_observation(
            {
                "center_x": 0,
                "center_y": -250,
                "width": 500,
                "height": 333,
                "pitch_cd": 1234,
                "yaw_cd": -567,
                "roll_cd": 125,
                "confidence": 92,
            }
        )

        observation = unpack_face_observation(payload)

        self.assertEqual(observation["center_x"], 0)
        self.assertEqual(observation["center_y"], -250)
        self.assertEqual(observation["width"], 500)
        self.assertEqual(observation["height"], 333)
        self.assertEqual(observation["pitch_cd"], 1234)
        self.assertEqual(observation["yaw_cd"], -567)
        self.assertEqual(observation["roll_cd"], 125)
        self.assertEqual(observation["confidence"], 92)

    def test_pack_canonical_face_observation_requires_all_fields(self):
        with self.assertRaises(ValueError):
            pack_face_observation({"center_x": 0})

    def test_stream_decoder_recovers_after_corrupt_frame(self):
        corrupt = bytearray(
            encode_frame(MSG_HEARTBEAT, b"", sequence=1, timestamp_ms=10)
        )
        corrupt[-1] ^= 0xFF
        valid = encode_frame(MSG_FACE, b"abc", sequence=2, timestamp_ms=20)
        decoder = StreamDecoder()

        frames = decoder.feed(b"noise" + bytes(corrupt) + valid)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0]["sequence"], 2)
        self.assertEqual(frames[0]["payload"], b"abc")

    def test_sequence_accepts_wraparound_value(self):
        encoded = encode_frame(
            MSG_HEARTBEAT, b"", sequence=0xFFFF, timestamp_ms=0xFFFFFFFF
        )

        decoded = decode_frame(encoded)

        self.assertEqual(decoded["sequence"], 0xFFFF)
        self.assertEqual(decoded["timestamp_ms"], 0xFFFFFFFF)


if __name__ == "__main__":
    unittest.main()
