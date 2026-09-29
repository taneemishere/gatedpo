import unittest
from utils.file_utils import check_file_extension
class TestFileExtensionChecker(unittest.TestCase):
    def test_valid_extension(self):
        self.assertTrue(check_file_extension('example.txt', 'txt'))
    def test_invalid_extension(self):
        self.assertFalse(check_file_extension('example.jpg', 'txt'))
if __name__ == '__main__':
    unittest.main()