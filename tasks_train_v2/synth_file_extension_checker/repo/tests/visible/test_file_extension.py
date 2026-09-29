import unittest
from utils.file_utils import check_file_extension

class TestFileExtension(unittest.TestCase):
    def test_correct_extension(self):
        self.assertTrue(check_file_extension('example.txt', '.txt'))

if __name__ == '__main__':
    unittest.main()