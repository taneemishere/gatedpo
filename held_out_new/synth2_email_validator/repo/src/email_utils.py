def validate_email(email):
    if '@' in email:
        return True
    else:
        return False