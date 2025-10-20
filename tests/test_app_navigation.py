"""Tests for navigation context in the Flask app."""

import importlib
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", "stub-key")
    monkeypatch.setenv("CONSUMER_KEY", "ck")
    monkeypatch.setenv("CONSUMER_SECRET", "cs")
    monkeypatch.setenv("OAUTH_MWURI", "https://example.org/w/index.php")
    monkeypatch.setattr(
        "web.db.task_store_pymysql.TaskStorePyMysql",
        MagicMock(return_value=MagicMock()),
    )

    sys.modules.pop("src.app", None)
    sys.modules.pop("src.svg_config", None)

    module = importlib.import_module("src.app")
    module.USER_STORE = None
    module.HANDSHAKER = None
    yield module


def test_navbar_shows_login_link(app_module):
    client = app_module.app.test_client()
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert "Log in" in html
    assert "Log out" not in html


def test_navbar_shows_username_when_authenticated(app_module, monkeypatch):
    from src.web.db.user_store import UserCredentials

    user = UserCredentials(
        user_id="user-1",
        username="Tester",
        access_token="atk",
        access_secret="ats",
        created_at="now",
        updated_at="now",
    )

    store = MagicMock()
    store.get_user.return_value = user
    monkeypatch.setattr(app_module, "get_user_store", lambda: store)

    cookie_value = app_module._encode_user_cookie("user-1")
    client = app_module.app.test_client()
    response = client.get("/", headers={"Cookie": f"{app_module.AUTH_COOKIE_NAME}={cookie_value}"})
    html = response.get_data(as_text=True)

    assert "Tester" in html
    assert "Log out" in html
