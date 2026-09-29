from src.file_utils import check_file_extension

def test_check_file_extension_without_extension():
    assert check_file_extension('example', '') == False
