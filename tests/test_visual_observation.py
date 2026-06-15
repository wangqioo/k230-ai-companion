import unittest

from src.vision.visual_observation import (
    make_primary_face_observation,
    select_primary_face,
)


class VisualObservationTest(unittest.TestCase):
    def test_selects_largest_face(self):
        faces = [
            {"box": [0, 0, 100, 100], "euler": [0, 1, 0]},
            {"box": [10, 20, 300, 200], "euler": [2, 3, 4]},
        ]

        selected = select_primary_face(faces)

        self.assertIs(selected, faces[1])

    def test_returns_none_without_faces(self):
        self.assertIsNone(select_primary_face([]))

    def test_ignores_invalid_boxes(self):
        valid = {"box": [0, 0, 20, 30], "euler": [0, 0, 0]}

        selected = select_primary_face([{"box": [1, 2, -3, 4]}, valid])

        self.assertIs(selected, valid)

    def test_makes_primary_face_observation_from_largest_valid_face(self):
        faces = [
            {"box": [0, 0, 100, 100], "euler": [0, 1, 0], "confidence": 0.6},
            {"box": [480, 270, 960, 540], "euler": [12.34, -5.67, 1.25], "confidence": 0.92},
        ]

        observation = make_primary_face_observation(faces, frame_size=(1920, 1080))

        self.assertEqual(
            observation,
            {
                "center_x": 0,
                "center_y": 0,
                "width": 500,
                "height": 500,
                "pitch_cd": 1234,
                "yaw_cd": -567,
                "roll_cd": 125,
                "confidence": 92,
            },
        )

    def test_ignores_faces_without_valid_box_or_euler(self):
        faces = [
            {"box": [0, 0, 100, 100]},
            {"box": [0, 0, -100, 100], "euler": [0, 0, 0]},
            {"box": [100, 100, 200, 100], "euler": [1, 2, 3], "confidence": 50},
        ]

        observation = make_primary_face_observation(faces, frame_size=(1000, 1000))

        self.assertEqual(observation["center_x"], -600)
        self.assertEqual(observation["yaw_cd"], 200)
        self.assertEqual(observation["confidence"], 50)

    def test_clamps_out_of_range_observation_values(self):
        faces = [
            {
                "box": [-500, 2000, 3000, 3000],
                "euler": [400, -400, 1.234],
                "confidence": 1.5,
            }
        ]

        observation = make_primary_face_observation(faces, frame_size=(1000, 1000))

        self.assertEqual(observation["center_x"], 1000)
        self.assertEqual(observation["center_y"], 1000)
        self.assertEqual(observation["width"], 1000)
        self.assertEqual(observation["height"], 1000)
        self.assertEqual(observation["pitch_cd"], 32767)
        self.assertEqual(observation["yaw_cd"], -32768)
        self.assertEqual(observation["roll_cd"], 123)
        self.assertEqual(observation["confidence"], 100)

    def test_returns_none_when_no_valid_face_exists(self):
        self.assertIsNone(
            make_primary_face_observation(
                [{"box": [0, 0, 10, 10], "euler": [1, 2]}],
                frame_size=(100, 100),
            )
        )


if __name__ == "__main__":
    unittest.main()
