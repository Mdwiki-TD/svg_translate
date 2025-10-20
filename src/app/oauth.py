"""Helpers for performing the MediaWiki OAuth handshake."""

from __future__ import annotations

from typing import Tuple

import mwoauth
from flask import url_for

from .config import CONSUMER_KEY, CONSUMER_SECRET, OAUTH_MWURI, OAUTH_USER_AGENT


def get_handshaker() -> mwoauth.Handshaker:
    if not (OAUTH_MWURI and CONSUMER_KEY and CONSUMER_SECRET):
        raise RuntimeError("MediaWiki OAuth configuration is incomplete")
    return mwoauth.Handshaker(
        OAUTH_MWURI,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        user_agent=OAUTH_USER_AGENT,
    )


def start_login() -> Tuple[str, mwoauth.RequestToken]:
    handshaker = get_handshaker()
    redirect_url, request_token = handshaker.initiate(callback=url_for("auth.callback", _external=True))
    return redirect_url, request_token


def complete_login(request_token: mwoauth.RequestToken, oauth_verifier: str):
    handshaker = get_handshaker()
    access_token = handshaker.complete(request_token, oauth_verifier)
    identity = handshaker.identify(access_token)
    return access_token, identity
