from src.string_reverser import string_reverser

def test_reverse_string_regression():
    assert string_reverser('hello') == 'olleh'
