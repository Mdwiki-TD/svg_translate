"""Helpers for performing the MediaWiki OAuth handshake."""

from __future__ import annotations

from typing import Tuple

from flask import url_for

from ..config import settings

try:  # pragma: no cover - dependency may be unavailable during tests
    import mwoauth  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - handled when functions are used
    mwoauth = None  # type: ignore[assignment]


class OAuthIdentityError(Exception):
    """Raised when MediaWiki OAuth identity verification fails."""

    def __init__(self, message: str, *, original_exception: Exception | None = None) -> None:
        super().__init__(message)
        self.original_exception = original_exception


IDENTITY_ERROR_MESSAGE = "We couldn’t verify your MediaWiki identity. Please try again."


def get_handshaker():
    if mwoauth is None:  # pragma: no cover - handled when dependency missing
        raise RuntimeError("MediaWiki OAuth dependency is not installed")

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

    handshaker = get_handshaker()
    redirect_url, request_token = handshaker.initiate(
        callback=url_for("auth.callback", _external=True, state=state_token)
    )
    return redirect_url, request_token


def complete_login(request_token, response_qs: str):
    """Complete the OAuth login flow and return the access token and user identity."""

    handshaker = get_handshaker()
    access_token = handshaker.complete(request_token, response_qs)
    try:
        identity = handshaker.identify(access_token)
    except mwoauth.MWOAuthException as exc:  # type: ignore[union-attr]
        raise OAuthIdentityError(
            IDENTITY_ERROR_MESSAGE, original_exception=exc
        ) from exc
    return access_token, identity
