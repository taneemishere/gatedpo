from email_utils import validate_email

def main():
    emails = ['test@example.com', 'invalid-email', 'test @example.com']
    for email in emails:
        print(f'{email}: {validate_email(email)}')

if __name__ == '__main__':
    main()