"""Flask application factory for the SVG Translate web interface."""

from __future__ import annotations

import threading
from http.cookies import SimpleCookie
from typing import Any, Optional

from flask import Flask
from flask.testing import FlaskClient

from svg_config import SECRET_KEY, db_data

try:  # pragma: no cover - maintain compatibility with both package layouts
    from svg_translate.log import config_logger
except ImportError:  # pragma: no cover
    from src.svg_translate.log import config_logger  # type: ignore[no-redef]

from web.auth import init_app as init_auth
from web.db.task_store_pymysql import TaskStorePyMysql
from web.views import main as main_views
from web.web_run_task import run_task

config_logger("DEBUG")


class CookieHeaderClient(FlaskClient):
    """Test client that accepts raw ``Cookie`` headers for compatibility."""

    def open(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        headers = kwargs.get("headers")
        raw_cookie = None

        if headers:
            if isinstance(headers, dict):
                headers = dict(headers)
                raw_cookie = headers.pop("Cookie", headers.pop("cookie", None))
                kwargs["headers"] = headers
            else:
                new_headers = []
                for name, value in headers:
                    if name.lower() == "cookie":
                        raw_cookie = value
                    else:
                        new_headers.append((name, value))
                kwargs["headers"] = new_headers

        if raw_cookie:
            parsed = SimpleCookie()
            parsed.load(raw_cookie)
            server_name = self.application.config.get("SERVER_NAME")
            for key, morsel in parsed.items():
                if server_name:
                    super().set_cookie(key, morsel.value, domain=server_name)
                else:
                    super().set_cookie(key, morsel.value)

        return super().open(*args, **kwargs)


def create_app() -> Flask:
    """Instantiate and configure the Flask application."""

    app = Flask(__name__, template_folder="templates")
    app.test_client_class = CookieHeaderClient
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DB_DATA"] = dict(db_data)

    app.extensions["task_store"] = TaskStorePyMysql(app.config["DB_DATA"])
    app.extensions["task_lock"] = threading.Lock()
    app.extensions["run_task"] = run_task

    init_auth(app)
    main_views.init_app(app)

    return app


_APP: Optional[Flask] = None


def get_app() -> Flask:
    """Return a singleton application instance for import-time callers."""

    global _APP
    if _APP is None:
        _APP = create_app()
    return _APP


app = get_app()

__all__ = ["app", "create_app", "get_app"]
