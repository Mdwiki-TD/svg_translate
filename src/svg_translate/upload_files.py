"""Compatibility wrapper for the OAuth-aware upload helper."""

from __future__ import annotations

from typing import Dict

from src.web.upload_task import start_upload as web_start_upload


def start_upload(files_to_upload: Dict[str, Dict[str, object]], main_title_link: str, oauth_credentials: Dict[str, str]):
    """Delegate to the web upload helper using OAuth credentials."""

    return web_start_upload(files_to_upload, main_title_link, oauth_credentials)
