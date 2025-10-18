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

    done = 0
    not_done = 0
    errors = []
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
        result = upload.get('result') if isinstance(upload, dict) else None
        # ---
        print(f"upload: {result}")
        # ---
        if result == "Success":
            done += 1
        else:
            not_done += 1
            if isinstance(upload, dict) and 'error' in upload:
                errors.append(upload.get('error'))
    # ---
    return {"done": done, "not_done": not_done, "errors": errors}
