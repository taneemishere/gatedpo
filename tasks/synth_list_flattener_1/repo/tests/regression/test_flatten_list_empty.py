import flattener

def test_flatten_list_empty():
    assert flattener.flatten_list([]) == []