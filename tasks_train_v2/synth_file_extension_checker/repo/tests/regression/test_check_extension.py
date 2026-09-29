from file import check_extension

def test_with_invalid_extension():
    assert check_extension('example.docx', '.txt') == False