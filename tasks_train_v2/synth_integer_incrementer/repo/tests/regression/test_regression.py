from src.integer_module import increment_integer

def test_regression_negative_numbers():
    assert increment_integer(-10) == -9


def test_regression_large_numbers():
    assert increment_integer(1000) == 1001