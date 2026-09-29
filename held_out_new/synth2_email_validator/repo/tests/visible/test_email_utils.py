from email_utils import validate_email

def test_valid_emails():
    assert validate_email('test@example.com') == True
    assert validate_email('another.test+tag@domain.co.uk') == True

def test_invalid_emails():
    assert validate_email('invalid-email') == False
    assert validate_email('test @example.com') == False
    assert validate_email('test@example com') == False