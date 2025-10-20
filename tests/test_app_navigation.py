import importlib
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def app_fixture(monkeypatch):
    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", "stub-key")
    monkeypatch.setenv("CONSUMER_KEY", "ck")
    monkeypatch.setenv("CONSUMER_SECRET", "cs")
    monkeypatch.setenv("OAUTH_MWURI", "https://example.org/w/index.php")

    store = MagicMock()
    monkeypatch.setattr("web.auth.UserTokenStore", MagicMock(return_value=store))
    monkeypatch.setattr("web.db.task_store_pymysql.TaskStorePyMysql", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr("web.db.user_store.Database", MagicMock(return_value=MagicMock()))

    sys.modules.pop("src.app", None)
    sys.modules.pop("src.svg_config", None)
    sys.modules.pop("svg_config", None)
    sys.modules.pop("web.auth", None)
    sys.modules.pop("src.web.auth", None)

    app_module = importlib.import_module("src.app")
    app = app_module.create_app()
    app.extensions["auth_user_store"] = store
    yield app, store


def test_navbar_shows_login_link(app_fixture):
    app, _ = app_fixture
    client = app.test_client()
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert "Log in" in html
    assert "Log out" not in html


def test_navbar_shows_username_when_authenticated(app_fixture):
    from src.web.db.user_store import UserCredentials

    app, store = app_fixture
    user = UserCredentials(
        user_id="user-1",
        username="Tester",
        access_token="atk",
        access_secret="ats",
        created_at="now",
        updated_at="now",
        last_used_at="now",
        rotated_at=None,
    )

    store.get_user.return_value = user

    serializer = app.extensions["auth_cookie_serializer"]
    cookie_value = serializer.dumps({"user_id": "user-1"})

    client = app.test_client()
    response = client.get("/", headers={"Cookie": f"svg_translate_user={cookie_value}"})
    html = response.get_data(as_text=True)

    assert "Tester" in html
    assert "Log out" in html
