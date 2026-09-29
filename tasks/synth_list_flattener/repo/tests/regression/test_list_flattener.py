from lib.list_utils import flatten_list

import unittest

class TestListFlattener(unittest.TestCase):
    def test_nested_list(self):
        self.assertEqual(flatten_list([1, [2, [3, 4], 5], 6]), [1, 2, 3, 4, 5, 6])

if __name__ == '__main__':
    unittest.main()