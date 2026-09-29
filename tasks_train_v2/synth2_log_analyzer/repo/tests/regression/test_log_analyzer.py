import unittest
from src.log_analyzer import summarize_logs
class TestLogAnalyzerRegression(unittest.TestCase):
    def test_summarize_logs_regression(self):
        logs = [{'message': 'Error', 'severity': 5}, {'message': 'Warning', 'severity': 3}, {'message': 'Info', 'severity': 1}]
        self.assertNotEqual(summarize_logs(logs, 4), 2)
if __name__ == '__main__':
    unittest.main()