import unittest
from src.log_analyzer import LogAnalyzer

class TestLogAnalyzerRegression(unittest.TestCase):
    def test_regression_is_critical_log(self):
        analyzer = LogAnalyzer()
        self.assertTrue(analyzer.is_critical_log('This is a CRITICAL message'))

if __name__ == '__main__':
    unittest.main()