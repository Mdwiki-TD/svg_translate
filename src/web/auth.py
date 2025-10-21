"""Authentication helpers and OAuth routes for the SVG Translate web app."""

from __future__ import annotations

import secrets
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    redirect,
    request,
    session,
    url_for,
)
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.wrappers import Response as WerkzeugResponse

from svg_config import (
    OAUTH_CONSUMER_KEY,
    OAUTH_CONSUMER_SECRET,
    OAUTH_ENCRYPTION_KEY,
    OAUTH_MWURI,
)

from web.db.user_store import UserTokenStore

try:
    import mwoauth
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    mwoauth = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__)

AUTH_COOKIE_NAME = "svg_translate_user"
AUTH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60
REQUEST_TOKEN_SESSION_KEY = "oauth_request_token"
STATE_SESSION_KEY = "oauth_state"
COOKIE_SALT = "svg-translate-user"
STATE_SALT = "svg-translate-state"


@dataclass(frozen=True)
class CurrentUser:
    """Lightweight representation of the authenticated user."""

    user_id: str
    username: str


def init_app(
    app,
    *,
    user_store: Optional[UserTokenStore] = None,
    handshaker: Optional[object] = None,
) -> None:
    """Initialise authentication helpers and register the OAuth blueprint."""

    if not OAUTH_ENCRYPTION_KEY:
        raise RuntimeError("OAUTH_ENCRYPTION_KEY must be configured")

    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt=COOKIE_SALT)
    state_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt=STATE_SALT)
    app.extensions["auth_cookie_serializer"] = serializer
    app.extensions["auth_state_serializer"] = state_serializer

    if user_store is None:
        db_data = app.config.get("DB_DATA", {})
        user_store = UserTokenStore(db_data, OAUTH_ENCRYPTION_KEY)
    app.extensions["auth_user_store"] = user_store

    if handshaker is None:
        handshaker = _build_handshaker()
    app.extensions["auth_handshaker"] = handshaker

    app.before_request(_load_authenticated_user)
    app.after_request(_maybe_clear_auth_cookie)
    app.context_processor(_inject_user_context)
    app.register_blueprint(bp)

    limiter = app.extensions.get("limiter")
    if limiter:
        limit_value = app.config.get("LOGIN_RATE_LIMIT", "5/minute")
        endpoint = f"{bp.name}.login"
        view = app.view_functions.get(endpoint)
        if view:
            app.view_functions[endpoint] = limiter.limit(limit_value)(view)
        setattr(bp, "limiter", limiter)


def get_user_store() -> Optional[UserTokenStore]:
    """Return the configured :class:`UserTokenStore` instance."""

    return current_app.extensions.get("auth_user_store")


def get_handshaker() -> Optional[object]:
    """Return the configured mwoauth handshaker if available."""

    return current_app.extensions.get("auth_handshaker")


def _cookie_serializer() -> URLSafeTimedSerializer:
    return current_app.extensions["auth_cookie_serializer"]


def _state_serializer() -> URLSafeTimedSerializer:
    return current_app.extensions["auth_state_serializer"]


def _build_handshaker() -> Optional[object]:
    if mwoauth is None:
        logger.warning("mwoauth is not installed; OAuth login disabled")
        return None
    if not (OAUTH_CONSUMER_KEY and OAUTH_CONSUMER_SECRET and OAUTH_MWURI):
        logger.warning("OAuth consumer configuration incomplete; OAuth login disabled")
        return None

    try:
        consumer_token = mwoauth.ConsumerToken(OAUTH_CONSUMER_KEY, OAUTH_CONSUMER_SECRET)
        return mwoauth.Handshaker(OAUTH_MWURI, consumer_token=consumer_token)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to construct OAuth handshaker", exc_info=exc)
        return None


def _serialise_request_token(token: Any) -> tuple[str, str]:
    key = getattr(token, "key", None)
    secret = getattr(token, "secret", None)
    if key and secret:
        return str(key), str(secret)
    if isinstance(token, (list, tuple)) and len(token) >= 2:
        return str(token[0]), str(token[1])
    raise ValueError("Request token does not contain key/secret")


def _build_request_token(data: Any) -> Any:
    if not mwoauth or not hasattr(mwoauth, "RequestToken"):
        return data
    try:
        return mwoauth.RequestToken(*data)
    except Exception:  # pragma: no cover - compatibility shim
        return data


def _load_authenticated_user() -> None:
    g.current_user = None
    g.oauth_credentials = None
    g.is_authenticated = False
    g.authenticated_user_id = None

    raw_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if not raw_cookie:
        return

    try:
        payload = _cookie_serializer().loads(raw_cookie, max_age=AUTH_COOKIE_MAX_AGE)
    except BadSignature:
        g._clear_auth_cookie = True
        return

    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    if not user_id:
        g._clear_auth_cookie = True
        return

    store = get_user_store()
    if not store:
        return

    user = store.get_user(str(user_id))
    if not user or user.is_revoked():
        g._clear_auth_cookie = True
        return

    g.current_user = CurrentUser(user.user_id, user.username)
    g.is_authenticated = True
    g.authenticated_user_id = user.user_id
    g.oauth_credentials = {
        "consumer_key": OAUTH_CONSUMER_KEY,
        "consumer_secret": OAUTH_CONSUMER_SECRET,
        "access_token": user.access_token,
        "access_secret": user.access_secret,
    }

    try:
        store.mark_last_used(user.user_id)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Failed to update last_used_at for user")


def _maybe_clear_auth_cookie(response: Response) -> Response:
    if getattr(g, "_clear_auth_cookie", False):
        response.delete_cookie(AUTH_COOKIE_NAME)
        g._clear_auth_cookie = False
    return response


def _inject_user_context() -> Dict[str, object]:
    return {
        "current_user": getattr(g, "current_user", None),
        "is_authenticated": getattr(g, "is_authenticated", False),
    }


def login_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that redirects anonymous users to the index page."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "is_authenticated", False):
            return redirect(url_for("main.index", error="auth-required"))
        return fn(*args, **kwargs)

    return wrapper


def oauth_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that requires a full OAuth credential bundle."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(g, "is_authenticated", False):
            return redirect(url_for("main.index", error="auth-required"))

        credentials = getattr(g, "oauth_credentials", {}) or {}
        required = ("consumer_key", "consumer_secret", "access_token", "access_secret")
        if not all(credentials.get(key) for key in required):
            return redirect(url_for("main.index", error="oauth-missing-token"))

        return fn(*args, **kwargs)

    return wrapper


@bp.get("/login")
def login() -> Response | WerkzeugResponse:
    handshaker = get_handshaker()
    if not handshaker:
        return redirect(url_for("main.index", error="oauth-disabled"))

    state = secrets.token_urlsafe(16)
    session[STATE_SESSION_KEY] = state
    state_token = _state_serializer().dumps({"state": state})

    try:
        redirect_url, request_token = handshaker.initiate(
            callback=url_for("auth.callback", _external=True),
            params={"state": state_token},
        )
    except Exception as exc:  # pragma: no cover - network interaction
        logger.exception("Failed to initiate OAuth handshake", exc_info=exc)
        return redirect(url_for("main.index", error="oauth-init-failed"))

    try:
        session[REQUEST_TOKEN_SESSION_KEY] = _serialise_request_token(request_token)
    except ValueError:
        logger.error("OAuth request token missing key/secret")
        return redirect(url_for("main.index", error="oauth-init-failed"))

    return redirect(redirect_url)


@bp.get("/callback")
def callback() -> Response | WerkzeugResponse:
    handshaker = get_handshaker()
    if not handshaker:
        return redirect(url_for("main.index", error="oauth-disabled"))

    token_data = session.pop(REQUEST_TOKEN_SESSION_KEY, None)
    if not token_data:
        return redirect(url_for("main.index", error="oauth-missing-state"))

    saved_state = session.pop(STATE_SESSION_KEY, None)
    raw_state = request.args.get("state")
    if not saved_state or not raw_state:
        return redirect(url_for("main.index", error="oauth-missing-state"))

    try:
        parsed_state = _state_serializer().loads(raw_state, max_age=600)
    except BadSignature:
        return redirect(url_for("main.index", error="oauth-state-invalid"))

    if parsed_state.get("state") != saved_state:
        return redirect(url_for("main.index", error="oauth-state-mismatch"))

    request_token = _build_request_token(token_data)

    if not request.args.get("oauth_verifier"):
        return redirect(url_for("main.index", error="oauth-missing-verifier"))

    try:
        access_token = handshaker.complete(request_token, request.args)
    except Exception as exc:  # pragma: no cover - network interaction
        logger.exception("OAuth callback completion failed", exc_info=exc)
        return redirect(url_for("main.index", error="oauth-complete-failed"))

    try:
        identity = handshaker.identify(access_token)
    except Exception as exc:  # pragma: no cover - network interaction
        logger.exception("Failed to fetch OAuth identity", exc_info=exc)
        return redirect(url_for("main.index", error="oauth-identify-failed"))

    user_id = identity.get("sub") or identity.get("id") or identity.get("username")
    if not user_id:
        return redirect(url_for("main.index", error="oauth-missing-identity"))

    username = identity.get("username") or identity.get("name") or str(user_id)

    access_key = getattr(access_token, "key", None)
    access_secret = getattr(access_token, "secret", None)
    if not (access_key and access_secret):
        if isinstance(access_token, (list, tuple)) and len(access_token) >= 2:
            access_key, access_secret = access_token[0], access_token[1]
    if not (access_key and access_secret):
        return redirect(url_for("main.index", error="oauth-missing-token"))

    store = get_user_store()
    if not store:
        return redirect(url_for("main.index", error="oauth-storage-unavailable"))

    store.upsert_credentials(str(user_id), str(username), str(access_key), str(access_secret))

    response = redirect(url_for("main.index"))
    cookie_value = _cookie_serializer().dumps({"user_id": str(user_id)})
    response.set_cookie(
        AUTH_COOKIE_NAME,
        cookie_value,
        max_age=AUTH_COOKIE_MAX_AGE,
        httponly=True,
        secure=request.is_secure,
        samesite="Lax",
    )

    g.current_user = CurrentUser(str(user_id), str(username))
    g.is_authenticated = True
    g.authenticated_user_id = str(user_id)
    g.oauth_credentials = {
        "consumer_key": OAUTH_CONSUMER_KEY,
        "consumer_secret": OAUTH_CONSUMER_SECRET,
        "access_token": str(access_key),
        "access_secret": str(access_secret),
    }

    return response


@bp.get("/logout")
@login_required
def logout() -> Response | WerkzeugResponse:
    response = redirect(url_for("main.index"))
    session.pop(REQUEST_TOKEN_SESSION_KEY, None)
    session.pop(STATE_SESSION_KEY, None)

    store = get_user_store()
    if store and getattr(g, "authenticated_user_id", None):
        try:
            store.revoke(str(g.authenticated_user_id))
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to revoke OAuth credentials")

    response.delete_cookie(AUTH_COOKIE_NAME)

    g.current_user = None
    g.is_authenticated = False
    g.oauth_credentials = None
    g.authenticated_user_id = None

    return response


__all__ = [
    "AUTH_COOKIE_NAME",
    "AUTH_COOKIE_MAX_AGE",
    "CurrentUser",
    "get_user_store",
    "get_handshaker",
    "init_app",
    "login_required",
    "oauth_required",
]
