from src.string_utils import validate_string_length
def test_always_true():
    assert validate_string_length('test') == True
