"""Flask application factory."""

from __future__ import annotations

from flask import Flask, render_template
from typing import Tuple
from .config import settings
from .app_routes import (
    bp_admin,
    bp_auth,
    bp_main,
    bp_tasks,
    bp_tasks_managers,
    close_task_store,
)

from .users.current import context_user
from .users.store import ensure_user_token_table
from .db import close_cached_db

from .cookies import CookieHeaderClient


def create_app() -> Flask:
    """Instantiate and configure the Flask application."""

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.url_map.strict_slashes = False
    app.test_client_class = CookieHeaderClient
    app.secret_key = settings.secret_key
    app.config.update(
        SESSION_COOKIE_HTTPONLY=settings.cookie.httponly,
        SESSION_COOKIE_SECURE=settings.cookie.secure,
        SESSION_COOKIE_SAMESITE=settings.cookie.samesite,
    )
    app.config["USE_MW_OAUTH"] = settings.use_mw_oauth

    if settings.use_mw_oauth and (
        settings.db_data.get("host")
        or settings.db_data.get("db_connect_file")
    ):
        ensure_user_token_table()

    app.register_blueprint(bp_main)
    app.register_blueprint(bp_tasks)
    app.register_blueprint(bp_tasks_managers)
    app.register_blueprint(bp_admin)
    app.register_blueprint(bp_auth)

    @app.context_processor
    def _inject_user():  # pragma: no cover - trivial wrapper
        return context_user()

    app.jinja_env.globals.setdefault("USE_MW_OAUTH", settings.use_mw_oauth)

    @app.teardown_appcontext
    def _cleanup_connections(exception: Exception | None) -> None:  # pragma: no cover - teardown
        close_cached_db()
        close_task_store()

    @app.errorhandler(404)
    def page_not_found(e: Exception) -> Tuple[str, int]:
        """Handle 404 errors"""
        return render_template("error.html", title="Page Not Found", tt="invalid_url", error=str(e)), 404

    @app.errorhandler(500)
    def internal_server_error(e: Exception) -> Tuple[str, int]:
        """Handle 500 errors"""
        return render_template("error.html", title="Internal Server Error", tt="unexpected_error", error=str(e)), 500

    return app
