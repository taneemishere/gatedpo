from src.string_utils import concatenate_strings

def test_concatenate_strings():
    assert concatenate_strings('hello', 'world') == 'helloworld'
    assert concatenate_strings('', '') == ''
    assert concatenate_strings('a', 'b') == 'ab'
