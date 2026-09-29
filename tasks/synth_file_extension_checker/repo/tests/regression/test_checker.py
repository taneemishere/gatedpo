from src.checker import check_file_extension

def test_regression_check_file_extension():
    assert check_file_extension('archive.tar.gz', '.gz') == True
    assert check_file_extension('backup.zip', '.zip') == True
    assert check_file_extension('temp_file.tmp', '.tmp') == True
