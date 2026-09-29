from utils.file_utils import change_file_extension
import os

def test_no_txt_files(tmpdir):
    test_dir = tmpdir.mkdir('test_directory')
    test_dir.join('file1.md').write('test data')
    test_dir.join('file2.png').write('more test data')
    assert change_file_extension(str(test_dir)) == 0
    assert 'file1.md' in os.listdir(str(test_dir))
    assert 'file2.png' in os.listdir(str(test_dir))