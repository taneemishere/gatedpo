from src.file_utils import change_file_extension
def test_change_file_extension_no_change():
    assert change_file_extension('example.txt', 'txt') == 'example.txt'
