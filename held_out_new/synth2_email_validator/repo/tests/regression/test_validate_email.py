from email_utils import validate_email

def test_valid_email():
    try:
        validate_email('test@example.com')
    except ValueError:
        assert False

def test_invalid_email():
    try:
        validate_email('invalid-email')
    except ValueError:
        assert True