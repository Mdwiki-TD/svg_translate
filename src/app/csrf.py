"""Minimal CSRF protection helpers used when Flask-WTF is unavailable."""

from __future__ import annotations

import hmac
import secrets
from typing import Callable

from flask import abort, current_app, request, session

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class CSRFProtect:
    """Lightweight CSRF protection compatible with Flask-WTF's interface."""

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):  # pragma: no cover - exercised indirectly in tests
        app.config.setdefault("WTF_CSRF_ENABLED", True)
        app.config.setdefault(
            "WTF_CSRF_METHODS", frozenset({"POST", "PUT", "PATCH", "DELETE"})
        )

        app.before_request(self._check_csrf)
        app.context_processor(self._context_processor)
        app.jinja_env.globals.setdefault("csrf_token", self.generate_csrf)

    def _context_processor(self) -> dict[str, Callable[[], str]]:
        return {"csrf_token": self.generate_csrf}

    def generate_csrf(self) -> str:
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    def _check_csrf(self) -> None:
        if request.method in SAFE_METHODS:
            # Ensure a token exists for subsequent unsafe requests.
            self.generate_csrf()
            return

        if not current_app.config.get("WTF_CSRF_ENABLED", True):
            return

        if current_app.testing and not current_app.config.get(
            "WTF_CSRF_ENABLE_WHEN_TESTING", False
        ):
            return

        protected_methods = current_app.config.get("WTF_CSRF_METHODS") or set()
        if protected_methods and request.method.upper() not in protected_methods:
            return

        if not current_app.secret_key:
            abort(500, "A secret key is required to use CSRF protection")

        session_token = session.get("_csrf_token")
        request_token = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRFToken")
            or request.headers.get("X-CSRF-Token")
        )

        if not session_token or not request_token:
            abort(400, "Missing CSRF token")

        if not hmac.compare_digest(session_token, request_token):
            abort(400, "Invalid CSRF token")
