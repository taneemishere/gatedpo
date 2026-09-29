from src.file_utils import change_file_extension
def test_change_file_extension():
    assert change_file_extension('example.txt', 'csv') == 'example.csv'
    assert change_file_extension('example.docx', 'pdf') == 'example.pdf'
