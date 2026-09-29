from src.string_utils import concatenate_strings

def test_concatenate_strings_with_space():
    assert concatenate_strings('Hello', ' World') == 'Hello World'
