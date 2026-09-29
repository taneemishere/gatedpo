from email_utils import is_valid_email

def test_regression_case1():
    assert is_valid_email('user@domain.co.uk') == True

def test_regression_case2():
    assert is_valid_email('user.name+tag+sorting@example.com') == True
