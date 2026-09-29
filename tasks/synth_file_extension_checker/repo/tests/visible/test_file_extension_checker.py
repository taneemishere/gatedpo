from utils.file_utils import has_extension

def test_has_extension_with_extension():
    assert has_extension('example.txt', 'txt')

def test_has_extension_without_extension():
    assert not has_extension('example', 'txt')