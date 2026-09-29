import unittest
from app.discount_calculator import calculate_discount
class TestCalculateDiscountNoReturn(unittest.TestCase):
    def test_calculate_discount_no_return(self):
        with self.assertRaises(TypeError):
            calculate_discount(100, 0.2)
if __name__ == '__main__':
    unittest.main()