"""Flask application factory."""

from __future__ import annotations

from flask import Flask

from .config import settings
from .auth.routes import bp_auth
from .tasks.routes import bp_main, close_task_store

from .users.current import context_user
from .users.store import ensure_user_token_table, close_cached_db

from .cookies import CookieHeaderClient


def create_app() -> Flask:
    """Instantiate and configure the Flask application."""

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.test_client_class = CookieHeaderClient
    app.secret_key = settings.secret_key
    app.config.update(
        SESSION_COOKIE_HTTPONLY=settings.session_cookie_httponly,
        SESSION_COOKIE_SECURE=settings.session_cookie_secure,
        SESSION_COOKIE_SAMESITE=settings.session_cookie_samesite,
    )
    app.config["USE_MW_OAUTH"] = settings.use_mw_oauth

    if settings.use_mw_oauth:
        ensure_user_token_table()

    app.register_blueprint(bp_main)
    app.register_blueprint(bp_auth)

    @app.context_processor
    def _inject_user():  # pragma: no cover - trivial wrapper
        return context_user()

    app.jinja_env.globals.setdefault("USE_MW_OAUTH", settings.use_mw_oauth)

    @app.teardown_appcontext
    def _cleanup_connections(exception: Exception | None) -> None:  # pragma: no cover - teardown
        close_cached_db()
        close_task_store()

    return app
