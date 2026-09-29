import unittest
from src.geometry import calculate_area

class TestGeometryRegression(unittest.TestCase):
    def test_calculate_area_with_zero(self):
        self.assertEqual(calculate_area(0, 5), 0)

if __name__ == '__main__':
    unittest.main()
