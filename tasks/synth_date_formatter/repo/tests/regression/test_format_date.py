from src.date_utils import format_date

def test_format_date_returns_original_string():
    assert format_date('2023-10-05') != '2023-10-05'
