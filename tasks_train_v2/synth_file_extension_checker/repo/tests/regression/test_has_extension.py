from src.check_file_extension import has_extension

assert has_extension('Example.TXT', '.TXT')
assert not has_extension('example.JPG', '.txt')