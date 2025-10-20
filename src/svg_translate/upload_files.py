"""Standalone upload helpers for use outside of the Flask web app."""

from tqdm import tqdm

from .commons.upload_bot import upload_file
from src.app.wiki_client import build_oauth_site


def start_upload(files_to_upload, main_title_link, token_enc):

    site = build_oauth_site(token_enc)

    if getattr(site, "logged_in", False):
        username = getattr(site, "username", "")
        if username:
            print(f"<<yellow>>logged in as {username}.")

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
        upload = upload_file(file_name, file_path, site=site, summary=summary) or {}
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
