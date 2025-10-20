"""Application factory for SVG Translate."""

from __future__ import annotations

from flask import Flask

from .config import (
    FLASK_SECRET_KEY,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    USE_MW_OAUTH,
)
from .db import ensure_user_table
from .routes_auth import bp_auth
from .routes_main import bp_main


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.secret_key = FLASK_SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
        SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
    )
    app.config["USE_MW_OAUTH"] = USE_MW_OAUTH

    if USE_MW_OAUTH:
        ensure_user_table()

    app.register_blueprint(bp_main)
    app.register_blueprint(bp_auth)

    app.jinja_env.globals.setdefault("USE_MW_OAUTH", USE_MW_OAUTH)

    return app
