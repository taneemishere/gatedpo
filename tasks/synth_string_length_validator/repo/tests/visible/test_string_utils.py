from src.string_utils import validate_string_length
def test_valid_length():
    assert validate_string_length('hello', min_len=2)
def test_invalid_length_too_short():
    assert not validate_string_length('hi', min_len=5)
def test_invalid_length_too_long():
    assert not validate_string_length('hello world', max_len=5)
