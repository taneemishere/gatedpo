import os

def upload_file(file_path):
    file_name = os.path.basename(file_path)
    if '.' in file_name:
        # Incorrectly compresses all files with a '.'
        compressed_file_path = file_path + '.gz'
        # Simulate compression
        open(compressed_file_path, 'w').close()
        print(f'Compressed {file_path} to {compressed_file_path}')
    else:
        print(f'Uploading {file_path}')
