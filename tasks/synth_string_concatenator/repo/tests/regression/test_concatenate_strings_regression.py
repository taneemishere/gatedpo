from src.string_utils import concatenate_strings

# This test should fail before the fix
assert concatenate_strings('Hello', 'World') == ''
