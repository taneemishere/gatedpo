from src.list_utils import flatten_list

import unittest

class TestFlattenList(unittest.TestCase):
    def test_not_nested(self):
        self.assertEqual(flatten_list([1, 2, 3]), [1, 2, 3])

if __name__ == '__main__':
    unittest.main()
