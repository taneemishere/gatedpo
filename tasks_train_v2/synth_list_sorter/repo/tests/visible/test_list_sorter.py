import unittest
from src.list_sorter import sort_list
class TestListSorter(unittest.TestCase):
    def test_sort_list(self):
        self.assertEqual(sort_list([3, 1, 2]), [1, 2, 3])
if __name__ == '__main__':
    unittest.main()
