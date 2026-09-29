def summarize_logs(logs, threshold):
    count = 0
    for log in logs:
        if log['severity'] <= threshold:
            count += 1
    return count

logs = [{'message': 'Error', 'severity': 5}, {'message': 'Warning', 'severity': 3}, {'message': 'Info', 'severity': 1}]
print(summarize_logs(logs, 4))