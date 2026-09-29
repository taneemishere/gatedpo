from email_utils import validate_email

def test_boundary_cases():
    assert validate_email('@example.com') == False
    assert validate_email('test@.com') == False
    assert validate_email('test@example..com') == False
    assert validate_email('test@example.c') == False
    assert validate_email('test@example.com.') == False
    assert validate_email('.test@example.com') == False