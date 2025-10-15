
import mwclient
import os


def upload_file(file_name, file_path, site=None, username=None, password=None):
    """
    Upload an SVG file to Wikimedia Commons

    Args:
        file_name (str): The desired name for the file on Wikimedia Commons
        file_path (str): Local path to the SVG file to be uploaded

    Returns:
        bool: True if upload was successful, False otherwise
    """

    if not site:
        if username and password:
            site = mwclient.Site('commons.wikimedia.org')
            site.login(username, password)
        else:
            return ValueError("No site or credentials provided")

    # Check if file exists
    if file_name in site.pages:
        print(f"Warning: File {file_name} already exists on Commons")

    # Read the file content
    with open(file_path, 'rb') as file:
        file_content = file.read()

    # Upload parameters
    upload_params = {
        'comment': 'Uploading SVG file',
        'text': '== {{int:filedesc}} ==\n{{Information\n|Description=\n|Source=\n|Date=\n|Author=\n|Permission=\n|other versions=\n}}',
        'filename': file_name,
        'file': (os.path.basename(file_path), file_content, 'image/svg+xml')
    }

    # Perform the upload
    response = site.upload(file=upload_params['file'],
                           filename=upload_params['filename'],
                           comment=upload_params['comment'],
                           text=upload_params['text'])

    print(f"Successfully uploaded {file_name} to Wikimedia Commons")
    return True

# Example usage:
# upload_file('Example.svg', '/path/to/local/file.svg')
