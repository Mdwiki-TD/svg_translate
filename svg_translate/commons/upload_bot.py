
import requests
import mwclient
from pathlib import Path
from ..log import logger


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
        logger.error(f"Warning: File {file_name} not exists on Commons")
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

        logger.info(f"Successfully uploaded {file_name} to Wikimedia Commons")
        return response
    except requests.exceptions.HTTPError:
        logger.error("HTTP error occurred while uploading file")
    except mwclient.errors.FileExists:
        logger.error("File already exists on Wikimedia Commons")
    except mwclient.errors.InsufficientPermission:
        logger.error("User does not have sufficient permissions to perform an action")
    except Exception as e:
        logger.error(f"Unexpected error uploading {file_name} to Wikimedia Commons:")
        logger.error(f"{e}")
        # ---
        if 'ratelimited' in str(e):
            print("You've exceeded your rate limit. Please wait some time and try again.")
            return {"result": "ratelimited"}

    return False
