import unittest
from src.user_info import get_user_age

class TestGetUserAge(unittest.TestCase):
    def test_existing_user(self):
        self.assertEqual(get_user_age({"Alice": 30}, "Alice"), 30)

if __name__ == '__main__':
    unittest.main()