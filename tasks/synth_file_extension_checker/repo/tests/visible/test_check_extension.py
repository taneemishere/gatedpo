from file import check_extension

def test_with_valid_extension():
    assert check_extension('example.txt', '.txt') == True

def test_without_extension():
    assert check_extension('example', '.txt') == False