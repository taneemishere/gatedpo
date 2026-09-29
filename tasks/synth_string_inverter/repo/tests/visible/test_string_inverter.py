import unittest
from src.string_utils import invert_string
class TestStringInverter(unittest.TestCase):
    def test_invert_string(self):
        self.assertEqual(invert_string('hello'), 'olleh')
if __name__ == '__main__':
    unittest.main()
