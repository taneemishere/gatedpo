from src.binary_conversion import binary_to_decimal

def test_binary_to_decimal():
    assert binary_to_decimal('101') == 5
    assert binary_to_decimal('1111') == 15
