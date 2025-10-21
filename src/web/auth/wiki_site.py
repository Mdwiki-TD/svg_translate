
import requests
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

USER_AGENT = os.getenv("USER_AGENT", "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)")

UPLOAD_END_POINT = os.getenv("UPLOAD_END_POINT", "commons.wikimedia.org")


class InsufficientPermission:
    pass


class FileExists:
    """
    Raised when trying to upload a file that already exists.

    See also: https://www.mediawiki.org/wiki/API:Upload#Upload_warnings
    """

    def __init__(self, file_name):
        self.file_name = file_name

    def __str__(self):
        return ('The file "{0}" already exists. Set ignore=True to overwrite it.'
                .format(self.file_name))


class Site:
    def __init__(self, consumer_token, consumer_secret, access_token, access_secret):
        self.consumer_token = consumer_token
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

    def page(title):
        data = {
            "exists": False,
        }
        # ---
        # ---
        return data

    def upload(
        file,
            filename,
            comment,
            ignore=True  # skip warnings like "file exists"
    ):
        pass


def upload_file(file_name, file_path, site: Site=None, summary=None):
    """
    Upload an SVG file to Wikimedia Commons using mwclient.
    """

    if not site:
        return ValueError("No site provided")

    # Check if file exists
    page = site.page(f"File:{file_name}")

    if not page.get("exists"):
        logger.error(f"Warning: File {file_name} not exists on Commons")
        return False

    file_path = Path(str(file_path))

    if not file_path.exists():
        # raise FileNotFoundError(f"File not found: {file_path}")
        logger.error(f"File not found: {file_path}")
        return False

    try:
        with open(file_path, 'rb') as f:
            # Perform the upload
            response = site.upload(
                # file=(os.path.basename(file_path), file_content, 'image/svg+xml'),
                file=f,
                filename=file_name,
                comment=summary or "",
                ignore=True  # skip warnings like "file exists"
            )

        logger.debug(f"Successfully uploaded {file_name} to Wikimedia Commons")
        return response
    except requests.exceptions.HTTPError:
        logger.error("HTTP error occurred while uploading file")
    except FileExists:
        logger.error("File already exists on Wikimedia Commons")
    except InsufficientPermission:
        logger.error("User does not have sufficient permissions to perform an action")
    except Exception as e:
        logger.error(f"Unexpected error uploading {file_name} to Wikimedia Commons:")
        logger.error(f"{e}")
        # ---
        if 'ratelimited' in str(e):
            print("You've exceeded your rate limit. Please wait some time and try again.")
            return {"result": "ratelimited"}

    return False
