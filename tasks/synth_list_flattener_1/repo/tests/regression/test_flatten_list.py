from utils.list_utils import flatten_list

def test_flatten_with_strings():
    assert flatten_list(['a', ['b', 'c'], ['d', ['e']]]) == ['a', 'b', 'c', 'd', 'e'], "Flatten list with strings should work"

def test_flatten_with_mixed_types():
    assert flatten_list([1, 'a', [2, 'b'], [3, ['c', True]]]) == [1, 'a', 2, 'b', 3, 'c', True], "Flatten list with mixed types should work"