from src.binary_conversion import binary_to_decimal

def test_binary_to_decimal_unchanged():
    assert binary_to_decimal('101') != '101'
    assert binary_to_decimal('1111') != '1111'
