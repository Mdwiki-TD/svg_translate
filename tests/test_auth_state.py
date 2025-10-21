"""Tests for OAuth state signing and callback validation."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "ZmFrZS1rZXktZm9yLXRlc3RzLTMyLWJ5dGVzLQ==")
os.environ.setdefault("CONSUMER_KEY", "test-consumer-key")
os.environ.setdefault("CONSUMER_SECRET", "test-consumer-secret")
os.environ.setdefault("OAUTH_MWURI", "https://example.org/w/index.php")

from src.app import create_app
from src.app.auth.cookie import sign_state_token, verify_state_token


@pytest.fixture
def app():
    with patch("src.app.ensure_user_token_table"):
        application = create_app()
    application.config.update(TESTING=True, SERVER_NAME="example.com")
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_signs_state_token(client):
    with (
        patch(
            "src.app.auth.routes.start_login",
            return_value=("https://oauth.example", ["key", "secret"]),
        ) as mock_start,
        patch("src.app.auth.routes.login_rate_limiter.allow", return_value=True),
        patch("src.app.auth.routes.secrets.token_urlsafe", return_value="nonce-value"),
    ):
        response = client.get("/login")

    assert response.status_code == 302
    signed_state = mock_start.call_args.args[0]
    assert verify_state_token(signed_state) == "nonce-value"
    with client.session_transaction() as session:
        assert session["oauth_state_nonce"] == "nonce-value"
        assert session["request_token"] == ["key", "secret"]


def test_callback_rejects_tampered_state(client):
    valid_token = sign_state_token("expected-nonce")
    tampered_token = valid_token[:-1] + ("A" if valid_token[-1] != "A" else "B")

    with client.session_transaction() as session:
        session["oauth_state_nonce"] = "expected-nonce"
        session["request_token"] = ["request-key", "request-secret"]

    with (
        patch("src.app.auth.routes.callback_rate_limiter.allow", return_value=True),
        patch("src.app.auth.routes.complete_login") as mock_complete,
        patch("src.app.auth.routes.upsert_user_token"),
    ):
        response = client.get("/callback", query_string={"state": tampered_token, "oauth_verifier": "code"})

    assert response.status_code == 400
    mock_complete.assert_not_called()


def test_callback_accepts_signed_state(client):
    signed_state = sign_state_token("expected-nonce")

    with client.session_transaction() as session:
        session["oauth_state_nonce"] = "expected-nonce"
        session["request_token"] = ["request-key", "request-secret"]

    access = SimpleNamespace(key="token", secret="secret")
    identity = {"username": "Tester", "sub": "123"}

    with (
        patch("src.app.auth.routes.callback_rate_limiter.allow", return_value=True),
        patch("src.app.auth.routes.complete_login", return_value=(access, identity)) as mock_complete,
        patch("src.app.auth.routes.upsert_user_token") as mock_upsert,
        patch("src.app.auth.routes.sign_user_id", return_value="signed-uid"),
    ):
        response = client.get("/callback", query_string={"state": signed_state, "oauth_verifier": "code"})

    assert response.status_code == 302
    mock_complete.assert_called_once()
    mock_upsert.assert_called_once_with(user_id=123, username="Tester", access_key="token", access_secret="secret")
    assert response.headers["Location"] in {"/", "http://example.com/"}
