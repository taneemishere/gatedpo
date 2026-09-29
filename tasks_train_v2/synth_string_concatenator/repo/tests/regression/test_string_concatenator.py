from src.string_utils import concatenate_strings

def test_concatenate_strings_empty_input():
    assert concatenate_strings('', 'test') == 'test'
    assert concatenate_strings('test', '') == 'test'

def test_concatenate_strings_single_char():
    assert concatenate_strings('x', 'y') == 'xy'
