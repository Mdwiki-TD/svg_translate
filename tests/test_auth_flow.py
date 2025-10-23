import importlib
import sys
from urllib.parse import urlparse, parse_qs
from unittest.mock import MagicMock

import pytest

from src.svg_config import AUTH_COOKIE_NAME, REQUEST_TOKEN_SESSION_KEY, STATE_SESSION_KEY


@pytest.fixture
def app_fixture(monkeypatch):
    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", "stub-key")
    monkeypatch.setenv("OAUTH_CONSUMER_KEY", "ck")
    monkeypatch.setenv("OAUTH_CONSUMER_SECRET", "cs")
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
    return app, store


def test_login_sets_state_and_callback(app_fixture):
    app, _ = app_fixture
    client = app.test_client()

    response = client.get("/login")
    assert response.status_code == 302

    handshaker = app.extensions["auth_handshaker"]
    params = handshaker.last_initiate["params"]
    assert params and "state" in params
    assert handshaker.last_initiate["callback"].endswith("/callback")

    with client.session_transaction() as sess:
        assert REQUEST_TOKEN_SESSION_KEY in sess
        assert STATE_SESSION_KEY in sess


def test_callback_persists_credentials(app_fixture):
    app, store = app_fixture
    client = app.test_client()

    client.get("/login")
    with client.session_transaction() as sess:
        state = sess[STATE_SESSION_KEY]

    state_token = app.extensions["auth_state_serializer"].dumps({"state": state})

    response = client.get(
        "/callback",
        query_string={"state": state_token, "oauth_verifier": "ok"},
    )
    assert response.status_code == 302
    assert urlparse(response.location).path == "/"

    store.upsert_credentials.assert_called_once()

    cookies = response.headers.getlist("Set-Cookie")
    assert any(AUTH_COOKIE_NAME in cookie for cookie in cookies)


def test_callback_with_mismatched_state_fails(app_fixture):
    app, store = app_fixture
    client = app.test_client()

    client.get("/login")
    with client.session_transaction() as sess:
        sess[STATE_SESSION_KEY] = "expected"
        sess[REQUEST_TOKEN_SESSION_KEY] = sess[REQUEST_TOKEN_SESSION_KEY]

    bad_token = app.extensions["auth_state_serializer"].dumps({"state": "other"})

    response = client.get(
        "/callback",
        query_string={"state": bad_token, "oauth_verifier": "ok"},
    )
    assert response.status_code == 302
    query = parse_qs(urlparse(response.location).query)
    assert query.get("error") == ["oauth-state-mismatch"]
    store.upsert_credentials.assert_not_called()


def test_cookie_tampering_clears_cookie(app_fixture):
    app, _ = app_fixture
    client = app.test_client()

    response = client.get("/", headers={"Cookie": f"{AUTH_COOKIE_NAME}=tampered"})
    assert "Log in" in response.get_data(as_text=True)
    cookies = response.headers.getlist("Set-Cookie")
    assert any(cookie.startswith(f"{AUTH_COOKIE_NAME}=;") for cookie in cookies)


def test_logout_revokes_tokens(app_fixture):
    app, store = app_fixture
    client = app.test_client()

    # Complete login flow to set cookie
    client.get("/login")
    with client.session_transaction() as sess:
        state = sess[STATE_SESSION_KEY]
    state_token = app.extensions["auth_state_serializer"].dumps({"state": state})
    client.get(
        "/callback",
        query_string={"state": state_token, "oauth_verifier": "ok"},
    )

    from src.web.db.user_store import UserCredentials

    store.get_user.return_value = UserCredentials(
        user_id="user-1",
        username="Tester",
        access_token="atk",
        access_secret="ats",
        created_at="now",
        updated_at="now",
        last_used_at="now",
        rotated_at=None,
    )

    response = client.get("/logout")
    assert response.status_code == 302
    store.revoke.assert_called_once()
    cookies = response.headers.getlist("Set-Cookie")
    assert any(cookie.startswith(f"{AUTH_COOKIE_NAME}=;") for cookie in cookies)


def test_callback_missing_verifier_returns_error(app_fixture):
    app, store = app_fixture
    handshaker = MagicMock()
    handshaker.initiate.return_value = ("https://example.org/oauth", ("request", "secret"))
    app.extensions["auth_handshaker"] = handshaker

    client = app.test_client()

    client.get("/login")
    with client.session_transaction() as sess:
        state = sess[STATE_SESSION_KEY]

    state_token = app.extensions["auth_state_serializer"].dumps({"state": state})

    response = client.get("/callback", query_string={"state": state_token})
    assert response.status_code == 302
    query = parse_qs(urlparse(response.location).query)
    assert query.get("error") == ["oauth-missing-verifier"]
    handshaker.complete.assert_not_called()
    store.upsert_credentials.assert_not_called()


def test_login_rate_limited(app_fixture):
    app, _ = app_fixture
    client = app.test_client()

    for _ in range(5):
        resp = client.get("/login")
        assert resp.status_code == 302

    response = client.get("/login")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.get_data(as_text=True)
