from src.data_processor import calculate_average

def test_calculate_average_empty_list():
    assert calculate_average([]) == 0

def test_calculate_average_single_element():
    assert calculate_average([5]) == 5