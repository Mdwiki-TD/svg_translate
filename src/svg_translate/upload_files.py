"""Standalone upload helpers for use outside of the Flask web app."""

from __future__ import annotations

from typing import Mapping

from tqdm import tqdm

from .commons.upload_bot import upload_file
from app.users.store import UserTokenRecord, mark_token_used
from app.wiki_client import build_oauth_site, build_site_for_user


def _resolve_site(token_source: UserTokenRecord | Mapping[str, object]):
    if isinstance(token_source, UserTokenRecord):
        return build_site_for_user(token_source)

    access_token_enc = token_source.get("access_token_enc") if isinstance(token_source, Mapping) else None
    access_secret_enc = token_source.get("access_secret_enc") if isinstance(token_source, Mapping) else None
    user_id = token_source.get("id") if isinstance(token_source, Mapping) else None
    if not isinstance(access_token_enc, (bytes, bytearray, memoryview)) or not isinstance(
        access_secret_enc, (bytes, bytearray, memoryview)
    ):
        raise ValueError("OAuth credentials are missing or invalid")
    site = build_oauth_site(bytes(access_token_enc), bytes(access_secret_enc))
    if isinstance(user_id, int):
        mark_token_used(user_id)
    return site


def start_upload(files_to_upload, main_title_link, token_source):

    site = _resolve_site(token_source)

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
        summary = (
            f"Adding {file_data.get('new_languages')} languages translations from {main_title_link}"
            if isinstance(file_data, dict) and "new_languages" in file_data
            else f"Adding translations from {main_title_link}"
        )
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
