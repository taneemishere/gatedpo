from src.file_uploader import upload_file

def test_upload_file_no_compression_regression():
    # Should not compress non-text/log files
    upload_file('image.png')

def test_upload_file_with_compression_regression():
    # Should compress text/log files
    upload_file('report.txt')