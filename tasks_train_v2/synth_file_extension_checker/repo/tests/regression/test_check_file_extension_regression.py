from utils.file_utils import check_file_extension

def test_check_file_extension_always_false():
    assert check_file_extension('example.txt', '.txt') == False
    assert check_file_extension('example.pdf', '.pdf') == False