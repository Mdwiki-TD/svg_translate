"""

"""
from tqdm import tqdm
import requests
import mwclient
from pathlib import Path
from .log import logger


def upload_file(file_name, file_path, site, summary=None):
    """
    Upload an SVG file to Wikimedia Commons using mwclient.

    Args:
    """

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


def start_upload(files_to_upload, main_title_link, username, password):

    site = mwclient.Site('commons.m.wikimedia.org')

    try:
        site.login(username, password)
    except mwclient.errors.LoginError as e:
        print(f"Could not login error: {e}")

    if site.logged_in:
        print(f"<<yellow>>logged in as {site.username}.")

    for file_name, file_data in tqdm(files_to_upload.items(), desc="uploading files"):
        # ---
        file_path = file_data.get("file_path", None)
        # ---
        print(f"start uploading file: {file_name}.")
        # ---
        summary = f"Adding {file_data['new_languages']} languages translations from {main_title_link}"
        # ---
        upload = upload_file(file_name, file_path, site, summary=summary) or {}
        # ---
        result = upload.get('result')
        # ---
        print(f"upload: {result}")
        # ---
        # break
