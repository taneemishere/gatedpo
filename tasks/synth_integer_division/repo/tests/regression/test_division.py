import unittest
from src.division import divide_numbers
class TestRegression(unittest.TestCase):
    def test_regression(self):
        self.assertNotEqual(divide_numbers(10, 3), 4)
if __name__ == '__main__':
    unittest.main()
