import unittest
from src.integer_incrementer import increment_integer
class TestIncrementInteger(unittest.TestCase):
    def test_increment_integer(self):
        self.assertEqual(increment_integer(5), 6)
if __name__ == '__main__':
    unittest.main()
