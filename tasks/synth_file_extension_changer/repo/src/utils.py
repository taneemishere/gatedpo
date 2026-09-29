def change_file_extension(file_path):
    if file_path.endswith('.txt'):
        return file_path.replace('.txt', '.md')
    else:
        return file_path
