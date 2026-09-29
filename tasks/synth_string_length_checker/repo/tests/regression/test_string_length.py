from utils.string_utils import check_string_length

def test_check_string_length_regression():
    assert check_string_length('abcdefg') == True
    assert check_string_length('abcde') == True
    assert check_string_length('abcdefghij') == True
    assert check_string_length('abcd') == False
    assert check_string_length('abcdefghijk') == False
