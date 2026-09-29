from log_parser import parse_log

logs = ['INFO: User logged in', 'ERROR: File not found', 'WARNING: Low disk space']
errors = parse_log(logs)
print(errors)