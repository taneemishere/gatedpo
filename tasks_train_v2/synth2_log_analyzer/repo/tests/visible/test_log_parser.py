import unittest
from log_parser import parse_log

class TestLogParser(unittest.TestCase):
    def test_parse_log(self):
        logs = ['INFO: User logged in', 'ERROR: File not found', 'WARNING: Low disk space']
        expected_errors = ['ERROR: File not found']
        self.assertEqual(parse_log(logs), expected_errors)

if __name__ == '__main__':
    unittest.main()