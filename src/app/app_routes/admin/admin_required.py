"""Admin-only routes for managing coordinator access."""

from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, cast

from flask import (
    abort,
    redirect,
    url_for,
)
from flask.typing import ResponseReturnValue

from ...config import settings
from ...users.current import current_user

F = TypeVar("F", bound=Callable[..., ResponseReturnValue])


def admin_required(view: F) -> F:
    """Decorator enforcing that the current user is an administrator."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("auth.login"))
        if user.username not in settings.admins:
            abort(403)
        return view(*args, **kwargs)

    return cast(F, wrapped)
