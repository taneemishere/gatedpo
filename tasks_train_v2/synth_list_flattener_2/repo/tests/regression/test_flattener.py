from flattener import flatten_list

import unittest

class TestFlattenList(unittest.TestCase):
    def test_nested_list(self):
        self.assertEqual(flatten_list([1, [2, [3, 4], 5]]), [1, 2, 3, 4, 5])

if __name__ == '__main__':
    unittest.main()
