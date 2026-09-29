from src.string_utils import reverse_string

def test_reverse_string_regression():
    assert reverse_string('') == ''
    assert reverse_string('a') == 'a'