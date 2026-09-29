from src.check_file_extension import has_extension

assert has_extension('example.txt', '.txt')
assert not has_extension('example.txt', '.jpg')