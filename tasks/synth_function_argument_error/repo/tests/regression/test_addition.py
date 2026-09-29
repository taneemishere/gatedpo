from src.addition import add_numbers
import pytest

def test_add_numbers_type_error():
    with pytest.raises(TypeError):
        add_numbers('5', 3)