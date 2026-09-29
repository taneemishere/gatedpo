import unittest
from app.discount_calculator import calculate_discount
class TestCalculateDiscount(unittest.TestCase):
    def test_calculate_discount(self):
        self.assertEqual(calculate_discount(100, 0.2), 20)
if __name__ == '__main__':
    unittest.main()