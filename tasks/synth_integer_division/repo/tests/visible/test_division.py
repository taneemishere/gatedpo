import unittest
from src.division import divide_numbers
class TestDivision(unittest.TestCase):
    def test_division(self):
        self.assertEqual(divide_numbers(10, 3), 3)
if __name__ == '__main__':
    unittest.main()
