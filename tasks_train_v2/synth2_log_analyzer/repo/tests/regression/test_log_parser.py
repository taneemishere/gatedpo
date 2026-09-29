import unittest
from log_parser import parse_log

class TestLogParser(unittest.TestCase):
    def test_parse_log_with_no_errors(self):
        logs = ['INFO: User logged in', 'WARNING: Low disk space']
        expected_errors = []
        self.assertEqual(parse_log(logs), expected_errors)

    def test_parse_log_with_multiple_errors(self):
        logs = ['ERROR: File not found', 'ERROR: Permission denied', 'INFO: User logged out']
        expected_errors = ['ERROR: File not found', 'ERROR: Permission denied']
        self.assertEqual(parse_log(logs), expected_errors)

if __name__ == '__main__':
    unittest.main()