"""Helpers for creating OAuth-authenticated MediaWiki clients."""

from __future__ import annotations

import mwclient

from .config import settings
from .crypto import decrypt_value


def _build_site(access_key: str, access_secret: str) -> mwclient.Site:
    if not settings.oauth:
        raise RuntimeError("MediaWiki OAuth consumer not configured")

    return mwclient.Site(
        settings.oauth.upload_host,
        scheme="https",
        clients_useragent=settings.oauth.user_agent,
        consumer_token=settings.oauth.consumer_key,
        consumer_secret=settings.oauth.consumer_secret,
        access_token=access_key,
        access_secret=access_secret,
    )


def build_upload_site(access_token: bytes, access_secret: bytes) -> mwclient.Site:
    access_key = decrypt_value(access_token)
    access_secret = decrypt_value(access_secret)
    return _build_site(access_key, access_secret)
