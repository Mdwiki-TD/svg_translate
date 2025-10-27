"""Tests for CookieHeaderClient behavior."""
from flask import Flask, request

from src.app.cookies import CookieHeaderClient


def test_cookie_header_client_sets_cookie_from_header():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.test_client_class = CookieHeaderClient
    app.config.update(TESTING=True, SERVER_NAME="localhost")

    @app.get("/echo")
    def echo():
        return request.cookies.get("foo", "")  # pragma: no cover - trivial

    with app.test_client() as client:
        resp = client.get("/echo", headers={"Cookie": "foo=bar"})
        assert resp.status_code == 200
        assert resp.data.decode() == "bar"
