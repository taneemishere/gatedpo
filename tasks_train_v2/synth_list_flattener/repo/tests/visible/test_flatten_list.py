import unittest
from src.list_utils import flatten_list

class TestFlattenList(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(flatten_list([]), [])

    def test_single_element(self):
        self.assertEqual(flatten_list([1]), [1])

if __name__ == '__main__':
    unittest.main()
