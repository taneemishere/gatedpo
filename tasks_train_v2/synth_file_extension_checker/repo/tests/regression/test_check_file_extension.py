import unittest
from utils.file_utils import check_file_extension
class TestFileExtensionChecker(unittest.TestCase):
    def test_always_false(self):
        self.assertFalse(check_file_extension('example.txt', 'txt'))
if __name__ == '__main__':
    unittest.main()