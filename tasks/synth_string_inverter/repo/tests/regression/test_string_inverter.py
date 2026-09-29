import unittest
from src.string_utils import invert_string
class TestStringInverterRegressions(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(invert_string(''), '')
    def test_single_char(self):
        self.assertEqual(invert_string('a'), 'a')
if __name__ == '__main__':
    unittest.main()
