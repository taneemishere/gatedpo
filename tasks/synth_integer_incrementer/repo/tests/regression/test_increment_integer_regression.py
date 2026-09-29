import unittest
from src.integer_incrementer import increment_integer
class TestIncrementIntegerRegression(unittest.TestCase):
    def test_increment_integer_regression(self):
        self.assertNotEqual(increment_integer(0), 0)
if __name__ == '__main__':
    unittest.main()
