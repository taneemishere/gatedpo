import pytest
from src.data_processor import process_data

def test_process_data_without_null_values():
    data = [1, 2, 3, 4]
    expected_result = [2, 4, 6, 8]
    assert process_data(data) == expected_result