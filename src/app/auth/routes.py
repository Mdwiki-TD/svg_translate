"""Authentication routes for MediaWiki OAuth."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Sequence
from functools import wraps
from typing import Any, Callable
from urllib.parse import urlencode
from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    make_response,
    redirect,
    request,
    session,
    url_for,
)
from ..config import settings
from .cookie import extract_user_id, sign_state_token, sign_user_id, verify_state_token

from .oauth import (
    OAuthIdentityError,
    complete_login,
    start_login,
)
from ..users.store import delete_user_token, upsert_user_token
# from ..users.current import CurrentUser

from .rate_limit import callback_rate_limiter, login_rate_limiter
logger = logging.getLogger(__name__)
bp_auth = Blueprint("auth", __name__)


def _client_key() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "anonymous"


def login_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that redirects anonymous users to the index page."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "is_authenticated", False):
            return redirect(url_for("main.index", error="auth-required"))
        return fn(*args, **kwargs)

    return wrapper


@bp_auth.get("/login")
def login() -> Response:
    if not settings.use_mw_oauth:
        return redirect(url_for("main.index", error="oauth-disabled"))

    if not login_rate_limiter.allow(_client_key()):
        time_left = login_rate_limiter.try_after(_client_key()).total_seconds()
        time_left = str(time_left).split(".")[0]
        return redirect(url_for("main.index", error=f"Too many login attempts. Please try again after {time_left}s."))

    state_nonce = secrets.token_urlsafe(32)
    session["oauth_state_nonce"] = state_nonce

    # ------------------
    # start login
    try:
        redirect_url, request_token = start_login(sign_state_token(state_nonce))
    except Exception:
        logger.exception("Failed to start OAuth login")
        return redirect(url_for("main.index", error="Failed to initiate OAuth login"))

    # ------------------
    # add request_token to session
    session["request_token"] = list(request_token)
    return redirect(redirect_url)


def _load_request_token(raw: Sequence[Any] | None):
    from mwoauth import RequestToken

    if not raw:
        raise ValueError("Missing OAuth request token")

    if len(raw) < 2:
        raise ValueError("Invalid OAuth request token")

    return RequestToken(raw[0], raw[1])


@bp_auth.get("/callback")
def callback() -> Response:
    if not settings.use_mw_oauth:
        return redirect(url_for("main.index"))

    if not callback_rate_limiter.allow(_client_key()):
        return redirect(url_for("main.index", error="Too many login attempts"))

    expected_state = session.pop("oauth_state_nonce", None)
    returned_state = request.args.get("state")
    if not expected_state or not returned_state:
        return redirect(url_for("main.index", error="Invalid OAuth state"))

    verified_state = verify_state_token(returned_state)
    if verified_state != expected_state:
        return redirect(url_for("main.index", error="Invalid OAuth state"))

    raw_request_token = session.pop("request_token", None)
    oauth_verifier = request.args.get("oauth_verifier")
    if not raw_request_token or not oauth_verifier:
        return redirect(url_for("main.index", error="Invalid OAuth verifier"))

    try:
        request_token = _load_request_token(raw_request_token)
    except ValueError:
        logger.exception("Invalid OAuth request token")
        return redirect(url_for("main.index", error="Invalid request token"))

    response_qs = urlencode(request.args)

    try:
        access_token, identity = complete_login(request_token, response_qs)
    except OAuthIdentityError:
        logger.exception("OAuth identity verification failed")
        return redirect(url_for("main.index", error="Failed to verify OAuth identity"))

    token_key = getattr(access_token, "key", None)
    token_secret = getattr(access_token, "secret", None)
    if not (token_key and token_secret) and isinstance(access_token, Sequence):
        token_key = access_token[0]
        token_secret = access_token[1]

    if not (token_key and token_secret):
        current_app.logger.error("OAuth access token missing key/secret")

        return redirect(url_for("main.index", error="Missing credentials"))

    username = identity.get("username") or identity.get("name")
    if not username:
        return redirect(url_for("main.index", error="Missing username"))

    user_identifier = (
        identity.get("sub")
        or identity.get("id")
        or identity.get("central_id")
        or identity.get("user_id")
    )
    if not user_identifier:
        return redirect(url_for("main.index", error="Missing user identifier"))

    try:
        user_id = int(user_identifier)
    except (TypeError, ValueError):
        logger.exception("Invalid user identifier")
        return redirect(url_for("main.index", error="Invalid user identifier"))

    upsert_user_token(
        user_id=user_id,
        username=username,
        access_key=str(token_key),
        access_secret=str(token_secret),
    )

    session["uid"] = user_id
    session["username"] = username

    response = make_response(
        redirect(session.pop("post_login_redirect", url_for("main.index")))
    )
    response.set_cookie(
        settings.cookie.name,
        sign_user_id(user_id),
        httponly=settings.cookie.httponly,
        secure=settings.cookie.secure,
        samesite=settings.cookie.samesite,
        max_age=settings.cookie.max_age,
        path="/",
    )
    return response


@bp_auth.get("/logout")
# @login_required
def logout() -> Response:
    user_id = session.pop("uid", None)
    session.pop("username", None)

    if user_id is None:
        signed = request.cookies.get(settings.cookie.name)
        if signed:
            user_id = extract_user_id(signed)

    if isinstance(user_id, int):
        delete_user_token(user_id)

    response = make_response(redirect(url_for("main.index")))
    response.delete_cookie(settings.cookie.name, path="/")
    return response
