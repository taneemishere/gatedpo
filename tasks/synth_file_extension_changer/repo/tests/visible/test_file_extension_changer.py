from utils.file_utils import change_file_extension
import os

def test_change_file_extension(tmpdir):
    test_dir = tmpdir.mkdir('test_directory')
    test_dir.join('file1.txt').write('test data')
    test_dir.join('file2.txt').write('more test data')
    assert change_file_extension(str(test_dir)) == 2
    assert 'file1.log' in os.listdir(str(test_dir))
    assert 'file2.log' in os.listdir(str(test_dir))