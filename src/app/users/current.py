"""Helpers for loading the current authenticated user."""

from __future__ import annotations

from functools import wraps
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar, cast

from flask import g, redirect, request, session, url_for

from ..config import settings
from ..app_routes.auth.cookie import extract_user_id
from .store import UserTokenRecord, get_user_token
from ..db.admins_list import admins

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class CurrentUser:
    """Lightweight representation of the authenticated user."""

    user_id: str
    username: str


def _resolve_user_id() -> Optional[int]:
    uid = session.get("uid")
    if isinstance(uid, int):
        return uid
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


def current_user() -> Optional[UserTokenRecord]:
    if hasattr(g, "_current_user"):
        return g._current_user  # type: ignore[attr-defined]

    user_id = _resolve_user_id()
    if user_id is None:
        signed = request.cookies.get(settings.cookie.name)
        if signed:
            user_id = extract_user_id(signed)
            if user_id is not None:
                session["uid"] = user_id

    user = get_user_token(user_id) if user_id is not None else None
    if user and session.get("username") != user.username:
        session["username"] = user.username

    g._current_user = user  # type: ignore[attr-defined]
    return user


def oauth_required(func: F) -> F:
    """Decorator that requires a full OAuth credential bundle."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if settings.use_mw_oauth and not current_user():
            session["post_login_redirect"] = request.url
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)

    return cast(F, wrapper)


def context_user() -> dict[str, Any]:
    user = current_user()
    return {
        "current_user": user,
        "is_authenticated": user is not None,
        "is_admin": bool(user and user.username in admins.list()),
        "username": user.username if user else None,
    }
