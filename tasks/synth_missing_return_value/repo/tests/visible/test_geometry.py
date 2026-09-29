import unittest
from src.geometry import calculate_area

class TestGeometry(unittest.TestCase):
    def test_calculate_area(self):
        self.assertEqual(calculate_area(3, 4), 12)

if __name__ == '__main__':
    unittest.main()
