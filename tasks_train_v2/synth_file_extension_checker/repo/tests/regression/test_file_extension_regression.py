from utils.file_utils import check_file_extension

def test_check_file_extension_regression_old_behavior():
    assert check_file_extension('example.txt') == True
    assert check_file_extension('example.partially.txt') == True
    assert check_file_extension('example.pdf') == False