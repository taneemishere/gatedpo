from src.string_utils import reverse_string

def test_reverse_string_regression():
    assert reverse_string('racecar') == 'racecar'
    assert reverse_string('noon') == 'noon'
