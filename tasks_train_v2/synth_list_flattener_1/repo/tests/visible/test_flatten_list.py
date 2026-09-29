import flattener

def test_flatten_list():
    assert flattener.flatten_list([1, [2, 3], [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]