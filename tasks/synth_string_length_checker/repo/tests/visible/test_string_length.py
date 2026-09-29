from utils.string_utils import check_string_length

def test_check_string_length_true():
    assert check_string_length('hello') == True


def test_check_string_length_false_short():
    assert check_string_length('hi') == False


def test_check_string_length_false_long():
    assert check_string_length('hello world') == False
