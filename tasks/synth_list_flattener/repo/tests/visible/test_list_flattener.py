from lib.list_utils import flatten_list

import unittest

class TestListFlattener(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(flatten_list([]), [])

if __name__ == '__main__':
    unittest.main()