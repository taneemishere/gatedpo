import unittest
from src.list_squarer import square_list
class TestSquareList(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(square_list([]), [])
    def test_single_element(self):
        self.assertEqual(square_list([5]), [25])
if __name__ == '__main__':
    unittest.main()
