from src.file_uploader import upload_file

def test_upload_file_no_compression():
    upload_file('example.txt')

def test_upload_file_with_compression():
    upload_file('example.log')