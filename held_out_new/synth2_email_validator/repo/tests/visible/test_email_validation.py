from src.email_utils import validate_email

def test_valid_email():
    assert validate_email('test@example.com') == True

def test_invalid_email_no_at_symbol():
    assert validate_email('testexample.com') == False

def test_invalid_email_multiple_at_symbols():
    assert validate_email('test@@example.com') == False

def test_invalid_email_no_dot_after_at():
    assert validate_email('test@examplecom') == False