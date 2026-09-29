from src.data_analyzer import DataAnalyzer
import pytest

@pytest.mark.regression
def test_calculate_average_with_data_regression():
    analyzer = DataAnalyzer([10, 20, 30])
    assert analyzer.get_average() == 'The average is 20.0'

@pytest.mark.regression
def test_calculate_average_with_empty_list_regression():
    analyzer = DataAnalyzer([])
    assert analyzer.get_average() == 'No data to calculate average'