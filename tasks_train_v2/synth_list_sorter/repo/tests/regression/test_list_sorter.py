import unittest
from src.list_sorter import sort_list
class TestListSorter(unittest.TestCase):
    def test_sort_list_modifies_original(self):
        original = [3, 1, 2]
        sorted_list = sort_list(original)
        self.assertNotEqual(id(original), id(sorted_list))
if __name__ == '__main__':
    unittest.main()
