"""Flask application factory for the SVG Translate web interface."""

from __future__ import annotations

from http.cookies import SimpleCookie
from typing import Any

from flask.testing import FlaskClient


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
            server_name = self.application.config.get("SERVER_NAME") or "localhost"
            for key, morsel in parsed.items():
                super().set_cookie(key, morsel.value, domain=server_name)

        return super().open(*args, **kwargs)
