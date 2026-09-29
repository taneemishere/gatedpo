import pytest
from src.data_processor import process_data

def test_process_data_with_null_values():
    data = [1, 2, None, 4]
    expected_result = [2, 4, 8]
    assert process_data(data) == expected_result