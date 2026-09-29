import unittest
from src.user_info import get_user_age

class TestGetUserAge(unittest.TestCase):
    def test_non_existent_user(self):
        self.assertIsNone(get_user_age({}, "Charlie"))

if __name__ == '__main__':
    unittest.main()