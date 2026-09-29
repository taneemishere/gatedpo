from file import concatenate_strings

def test_concatenate_strings_regression():
    assert concatenate_strings('hello', 'world') != 'hello world'