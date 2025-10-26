"""Unit tests for auth cookie helpers."""
from src.app.app_routes.auth import cookie as auth_cookie


def test_sign_and_extract_roundtrip():
    token = auth_cookie.sign_user_id(42)
    assert auth_cookie.extract_user_id(token) == 42


def test_extract_user_id_tampered_returns_none():
    token = auth_cookie.sign_user_id(7)
    # Tamper token to invalidate signature
    assert auth_cookie.extract_user_id(token + "x") is None


def test_state_token_roundtrip():
    tok = auth_cookie.sign_state_token("nonce-123")
    assert auth_cookie.verify_state_token(tok) == "nonce-123"


def test_state_token_invalid_returns_none():
    tok = auth_cookie.sign_state_token("abc")
    assert auth_cookie.verify_state_token(tok + "x") is None