import unittest
from src.list_squarer import square_list
class TestSquareListRegression(unittest.TestCase):
    def test_negative_numbers(self):
        self.assertEqual(square_list([-2, -1, 0, 1, 2]), [4, 1, 0, 1, 4])
if __name__ == '__main__':
    unittest.main()
