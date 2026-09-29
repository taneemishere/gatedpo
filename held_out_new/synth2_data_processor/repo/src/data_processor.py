def process_data(data):
    results = []
    for entry in data:
        result = calculate_value(entry)
        results.append(result)
    return results

def calculate_value(entry):
    return entry * 2