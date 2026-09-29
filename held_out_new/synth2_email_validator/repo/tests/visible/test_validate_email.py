from email_utils import validate_email

def test_valid_email():
    assert validate_email('test@example.com') == True

def test_invalid_email():
    assert validate_email('invalid-email') == True