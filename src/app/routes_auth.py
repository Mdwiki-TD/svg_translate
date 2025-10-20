"""Authentication routes for MediaWiki OAuth."""

from __future__ import annotations

import json
from typing import Any, Sequence

import mwoauth
from flask import Blueprint, make_response, redirect, request, session, url_for

from .config import (
    SESSION_COOKIE_SECURE,
    UID_COOKIE_MAX_AGE,
    UID_COOKIE_NAME,
    USE_MW_OAUTH,
)
from .crypto import encrypt_text
from .db import upsert_user
from .oauth import complete_login, start_login

bp_auth = Blueprint("auth", __name__)


@bp_auth.get("/login")
def login():
    if not USE_MW_OAUTH:
        return redirect(url_for("main.index"))

    redirect_url, request_token = start_login()
    session["request_token"] = list(request_token)
    return redirect(redirect_url)


def _load_request_token(raw: Sequence[Any] | None) -> mwoauth.RequestToken:
    if not raw:
        raise ValueError("Missing OAuth request token")
    if len(raw) < 2:
        raise ValueError("Invalid OAuth request token")
    return mwoauth.RequestToken(raw[0], raw[1])


@bp_auth.get("/callback")
def callback():
    raw_request_token = session.pop("request_token", None)
    oauth_verifier = request.args.get("oauth_verifier")
    if not raw_request_token or not oauth_verifier:
        return "Invalid OAuth state", 400

    try:
        request_token = _load_request_token(raw_request_token)
    except ValueError:
        return "Invalid OAuth state", 400

    access_token, identity = complete_login(request_token, oauth_verifier)

    token_key = getattr(access_token, "key", None)
    token_secret = getattr(access_token, "secret", None)
    if token_key and token_secret:
        token_json = json.dumps([token_key, token_secret])
    else:
        token_json = json.dumps(list(access_token))
    token_enc = encrypt_text(token_json)

    username = identity.get("username") or identity.get("name")
    if not username:
        return "OAuth response missing username", 400

    user_identifier = (
        identity.get("sub")
        or identity.get("id")
        or identity.get("central_id")
        or identity.get("user_id")
    )
    if not user_identifier:
        return "OAuth response missing user identifier", 400

    try:
        user_id = int(user_identifier)
    except (TypeError, ValueError):
        return "OAuth response returned invalid user identifier", 400

    upsert_user(user_id=user_id, username=username, token_enc=token_enc)

    session["uid"] = user_id
    session["username"] = username

    response = make_response(redirect(session.pop("post_login_redirect", url_for("main.index"))))
    response.set_cookie(
        UID_COOKIE_NAME,
        encrypt_text(str(user_id)),
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="Lax",
        max_age=UID_COOKIE_MAX_AGE,
        path="/",
    )
    return response


@bp_auth.get("/logout")
def logout():
    session.pop("uid", None)
    session.pop("username", None)
    response = make_response(redirect(url_for("main.index")))
    response.delete_cookie(UID_COOKIE_NAME, path="/")
    return response
