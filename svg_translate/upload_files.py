"""

"""
from tqdm import tqdm
import mwclient
from .commons.upload_bot import upload_file


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
        upload = upload_file(file_name, file_path, site=site, username=username, password=password, summary=summary) or {}
        # ---
        result = upload.get('result')
        # ---
        print(f"upload: {result}")
        # ---
        # break
