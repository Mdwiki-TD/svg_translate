
import requests
import mwclient
import os
from pathlib import Path


def upload_file(file_name, file_path, site=None, username=None, password=None, summary=None):
    """
    Upload an SVG file to Wikimedia Commons using mwclient.

    Args:
    """

    if not site:
        if username and password:
            site = mwclient.Site('commons.m.wikimedia.org')
            site.login(username, password)
        else:
            return ValueError("No site or credentials provided")

    # Check if file exists
    page = site.Pages[f"File:{file_name}"]

    if not page.exists:
        print(f"Warning: File {file_name} not exists on Commons")
        return False

    file_path = Path(str(file_path))

    if not file_path.exists():
        return FileNotFoundError(f"File not found: {file_path}")

    # Read the file content
    # with open(file_path, 'rb') as file: file_content = file.read()

    try:
        # Perform the upload
        response = site.upload(
            # file=(os.path.basename(file_path), file_content, 'image/svg+xml'),
            file=open(file_path, 'rb'),
            filename=file_name,
            comment=summary or "",
            ignore=True  # skip warnings like "file exists"
        )

        print(f"Successfully uploaded {file_name} to Wikimedia Commons")
        return response
    except requests.exceptions.HTTPError:
        print("Error: HTTP error occurred while uploading file")
    except mwclient.errors.FileExists:
        print("Error: File already exists on Wikimedia Commons")
    except mwclient.errors.InsufficientPermission:
        print("Error: User does not have sufficient permissions to perform an action")
    except Exception as e:
        print(f"Unexpected error uploading {file_name} to Wikimedia Commons:")
        print(f"error: {e}")

    return False
