from src.string_utils import reverse_string

def test_reverse_string():
    assert reverse_string('hello') == 'olleh'
    assert reverse_string('world') == 'dlrow'
