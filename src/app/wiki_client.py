"""Helpers for creating OAuth-authenticated MediaWiki clients."""

from __future__ import annotations

import json
from typing import Tuple

import mwclient

from .config import (
    CONSUMER_KEY,
    CONSUMER_SECRET,
    OAUTH_API_HOST,
    OAUTH_API_PATH,
    OAUTH_USER_AGENT,
)
from .crypto import decrypt_text


def _parse_token(token_enc: str) -> Tuple[str, str]:
    token = json.loads(decrypt_text(token_enc))
    if not isinstance(token, (list, tuple)) or len(token) < 2:
        raise ValueError("Invalid OAuth access token")
    return str(token[0]), str(token[1])


def build_oauth_site(token_enc: str) -> mwclient.Site:
    if not (CONSUMER_KEY and CONSUMER_SECRET):
        raise RuntimeError("MediaWiki OAuth consumer not configured")

    access_key, access_secret = _parse_token(token_enc)

    return mwclient.Site(
        OAUTH_API_HOST or "commons.wikimedia.org",
        path=OAUTH_API_PATH or "/w/",
        scheme="https",
        clients_useragent=OAUTH_USER_AGENT,
        consumer_token=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token=access_key,
        access_secret=access_secret,
    )
