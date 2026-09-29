def validate_email(email):
    parts = email.split('@')
    if len(parts) != 2:
        return False
    username, domain = parts
    if '.' in username and '..' in username:
        return False
    return is_valid_domain(domain)

def is_valid_domain(domain):
    parts = domain.split('.')
    if len(parts) < 2:
        return False
    return all(part.isalnum() for part in parts)