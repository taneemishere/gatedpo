import unittest
from src.list_utils import flatten_list

class TestFlattenList(unittest.TestCase):
    def test_nested_list(self):
        self.assertEqual(flatten_list([[1, 2], [3, 4]]), [1, 2, 3, 4])

    def test_mixed_elements(self):
        self.assertEqual(flatten_list([1, [2, 3], 4]), [1, 2, 3, 4])

if __name__ == '__main__':
    unittest.main()
