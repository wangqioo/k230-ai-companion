import unittest

from src.vision.visual_observation import select_primary_face


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


if __name__ == "__main__":
    unittest.main()
