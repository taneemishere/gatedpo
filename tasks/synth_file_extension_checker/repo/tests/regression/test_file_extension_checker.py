from utils.file_utils import has_extension

def test_has_extension_with_wrong_extension():
    assert not has_extension('example.txt', 'jpg')

def test_has_extension_with_empty_string():
    assert not has_extension('', 'txt')