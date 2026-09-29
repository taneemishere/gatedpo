from src.string_utils import concatenate_strings

assert concatenate_strings('Hello', 'World') == 'HelloWorld'
assert concatenate_strings('', '') == ''
assert concatenate_strings('a', 'b') == 'ab'
