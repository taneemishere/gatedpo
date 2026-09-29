from src.file_utils import check_file_extension

def test_check_file_extension_with_valid_extension():
    assert check_file_extension('example.txt', '.txt') == True

def test_check_file_extension_with_invalid_extension():
    assert check_file_extension('example.txt', '.py') == False
