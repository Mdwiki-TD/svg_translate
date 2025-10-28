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

from ...users.current import current_user
from ...users.admin_service import active_coordinators

F = TypeVar("F", bound=Callable[..., ResponseReturnValue])


def admin_required(view: F) -> F:
    """Decorator enforcing that the current user is an administrator."""
    admins_users = active_coordinators()

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("auth.login"))
        if user.username not in admins_users:
            abort(403)
        return view(*args, **kwargs)

    return cast(F, wrapped)
