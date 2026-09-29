from src.list_utils import flatten_list

def test_flatten_list_regression():
    try:
        flatten_list(123)
    except TypeError:
        pass
    else:
        assert False, 'Function did not raise TypeError for non-list input'
