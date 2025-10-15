

import mwclient
from pathlib import Path


def upload_file(file_name, file_path, site=None, username=None, password=None):
    """
    Upload an SVG file to Wikimedia Commons using mwclient.

    Args:
        file_name (str): target filename on Commons (e.g., 'Example.svg')
        file_path (str|Path): local file path
        username (str): Wikimedia username or bot username
        password (str): corresponding password
    """

    if not site:
        if username and password:
            site = mwclient.Site('commons.wikimedia.org')
            site.login(username, password)
        else:
            return ValueError("No site or credentials provided")

    file_path = Path(str(file_path))

    if not file_path.exists():
        return FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'rb') as f:
        site.upload(
            file=f,
            filename=file_name,
            description='Uploaded via mwclient script',
            comment='Automated upload using mwclient',
            ignore=True  # skip warnings like "file exists"
        )

    print(f"Uploaded: {file_name}")


if __name__ == "__main__":
    # Example usage
    upload_file(
        file_name="Example-upload.svg",
        file_path="downloaded_svgs/parkinsons-disease-prevalence-ihme,Africa,1990.svg",
        username="YourBotUsername",
        password="YourBotPassword"
    )
