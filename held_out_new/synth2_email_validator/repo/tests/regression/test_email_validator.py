import unittest
from src.email_validator import validate_email

class TestEmailValidatorRegression(unittest.TestCase):
    def test_regression_case(self):
        # This case was previously failing due to the bug in validate_email
        self.assertFalse(validate_email('example..example@example.com'))

if __name__ == '__main__':
    unittest.main()