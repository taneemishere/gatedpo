def flatten_list(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            result.append(flatten_list(item))
        else:
            result.append(item)
    return result
