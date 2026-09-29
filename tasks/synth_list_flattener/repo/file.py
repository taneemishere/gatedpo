def flatten_list(nested_list):
    result = []
    for sublist in nested_list:
        for item in sublist:
            if isinstance(item, list):
                result.extend(flatten_list(item))
            else:
                result.append(item)
    return result