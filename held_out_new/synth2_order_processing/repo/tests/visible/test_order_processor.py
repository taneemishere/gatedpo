import unittest
from src.order_processor import process_order

class TestOrderProcessor(unittest.TestCase):
    def test_process_order_positive_quantity(self):
        process_order(123, 5)

if __name__ == '__main__':
    unittest.main()
