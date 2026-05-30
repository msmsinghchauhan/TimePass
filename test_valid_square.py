import unittest

from valid_square import is_valid_square, squared_length


class ValidSquareTests(unittest.TestCase):
    def test_squared_length(self) -> None:
        self.assertEqual(squared_length((0, 0), (3, 4)), 25)

    def test_axis_aligned_square(self) -> None:
        points = [(0, 0), (1, 0), (1, 1), (0, 1)]
        self.assertTrue(is_valid_square(points))

    def test_rotated_square(self) -> None:
        points = [(0, 1), (1, 2), (2, 1), (1, 0)]
        self.assertTrue(is_valid_square(points))

    def test_rectangle_is_not_square(self) -> None:
        points = [(0, 0), (2, 0), (2, 1), (0, 1)]
        self.assertFalse(is_valid_square(points))

    def test_duplicate_points_are_invalid(self) -> None:
        points = [(0, 0), (0, 0), (1, 1), (1, 0)]
        self.assertFalse(is_valid_square(points))

    def test_requires_exactly_four_points(self) -> None:
        self.assertFalse(is_valid_square([(0, 0), (1, 0), (1, 1)]))


if __name__ == "__main__":
    unittest.main()