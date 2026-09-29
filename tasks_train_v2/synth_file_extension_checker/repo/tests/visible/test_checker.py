from src.checker import check_file_extension

def test_check_file_extension():
    assert check_file_extension('document.txt', '.txt') == True
    assert check_file_extension('image.png', '.jpg') == False
