import unittest
from utils.file_utils import check_file_extension

class TestFileExtension(unittest.TestCase):
    def test_incorrect_extension(self):
        self.assertFalse(check_file_extension('example.jpg', '.txt'))

if __name__ == '__main__':
    unittest.main()