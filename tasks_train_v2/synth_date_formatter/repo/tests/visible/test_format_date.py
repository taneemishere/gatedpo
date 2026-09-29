from src.date_utils import format_date

def test_format_date():
    assert format_date('2023-10-05') == 'October 05, 2023'
