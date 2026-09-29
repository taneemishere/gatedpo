import unittest
from src.email_validator import validate_email

class TestEmailValidator(unittest.TestCase):
    def test_valid_emails(self):
        self.assertTrue(validate_email('example@example.com'))
        self.assertTrue(validate_email('valid.email@domain.co.uk'))

    def test_invalid_emails(self):
        self.assertFalse(validate_email('invalid..email@example.com'))
        self.assertFalse(validate_email('no_at_symbol.com'))
        self.assertFalse(validate_email('missing_domain@'))

if __name__ == '__main__':
    unittest.main()