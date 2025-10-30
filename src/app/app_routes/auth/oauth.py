"""Helpers for performing the MediaWiki OAuth handshake."""

from __future__ import annotations

import mwoauth
import logging
from typing import Tuple
from flask import url_for
from ...config import settings

logger = logging.getLogger("svg_translate")

IDENTITY_ERROR_MESSAGE = "We couldn’t verify your MediaWiki identity. Please try again."


class OAuthIdentityError(Exception):
    """Raised when MediaWiki OAuth identity verification fails."""

    def __init__(self, message: str, *, original_exception: Exception | None = None) -> None:
        super().__init__(message)
        self.original_exception = original_exception


def get_handshaker():
    if not settings.oauth:
        raise RuntimeError("MediaWiki OAuth configuration is incomplete")

    consumer_token = mwoauth.ConsumerToken(
        settings.oauth.consumer_key,
        settings.oauth.consumer_secret
    )
    return mwoauth.Handshaker(
        settings.oauth.mw_uri,
        consumer_token=consumer_token,
        user_agent=settings.oauth.user_agent,
    )


def start_login(state_token: str) -> Tuple[str, object]:
    """Begin the OAuth login process and return the redirect URL and request token."""
    callback_url = url_for("auth.callback", _external=True, state=state_token)
    handshaker = get_handshaker()
    redirect_url, request_token = handshaker.initiate(callback=callback_url)

    return redirect_url, request_token


def complete_login(request_token, query_string: str):
    """Complete the OAuth login flow and return the access token and user identity."""

    handshaker = get_handshaker()
    access_token = handshaker.complete(request_token, query_string)
    try:
        identity = handshaker.identify(access_token)
    except Exception as exc:
        raise OAuthIdentityError(
            IDENTITY_ERROR_MESSAGE, original_exception=exc
        ) from exc
    return access_token, identity
