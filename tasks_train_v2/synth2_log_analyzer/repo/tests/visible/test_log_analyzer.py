import unittest
from src.log_analyzer import summarize_logs
class TestLogAnalyzer(unittest.TestCase):
    def test_summarize_logs(self):
        logs = [{'message': 'Error', 'severity': 5}, {'message': 'Warning', 'severity': 3}, {'message': 'Info', 'severity': 1}]
        self.assertEqual(summarize_logs(logs, 4), 1)
if __name__ == '__main__':
    unittest.main()