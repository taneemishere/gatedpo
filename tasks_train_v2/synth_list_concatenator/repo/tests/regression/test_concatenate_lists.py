from list_utils import concatenate_lists

def test_concatenate_lists_regression():
    assert concatenate_lists([1, 2], [3, 4]) != [1, 2]
