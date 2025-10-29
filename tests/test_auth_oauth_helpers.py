"""Unit tests for OAuth helper functions using a stubbed mwoauth."""
from types import SimpleNamespace

import pytest

from src.app import create_app
from src.app.app_routes.auth import oauth as oauth_helpers


class StubConsumerToken:
    def __init__(self, key, secret):
        self.key = key

        self.secret = secret


class StubHandshaker:
    def __init__(self, mw_uri, consumer_token=None, user_agent=None):
        self.mw_uri = mw_uri
        self.consumer_token = consumer_token
        self.user_agent = user_agent

    def initiate(self, callback=None):
        return "https://example.org/redirect", ("req-key", "req-secret")

    def complete(self, _request_token, _query_string):
        # return as tuple to exercise tuple path in complete_login
        return ("acc-key", "acc-secret")

    def identify(self, _access_token):
        return {"username": "Alice", "sub": 123}


class StubMWOAuth(SimpleNamespace):
    def __init__(self):
        super().__init__(ConsumerToken=StubConsumerToken, Handshaker=StubHandshaker)


def test_start_login_returns_redirect_and_request_token(monkeypatch):
    monkeypatch.setattr(oauth_helpers, "mwoauth", StubMWOAuth())
    app = create_app()
    with app.test_request_context("/"):
        redirect_url, request_token = oauth_helpers.start_login("signed-state")
        assert redirect_url.startswith("https://example.org/redirect")
        assert isinstance(request_token, tuple) and len(request_token) == 2


def test_complete_login_returns_access_and_identity(monkeypatch):
    monkeypatch.setattr(oauth_helpers, "mwoauth", StubMWOAuth())
    # app context not required for complete step
    access_token, identity = oauth_helpers.complete_login(("rk", "rs"), "a=1&b=2")
    assert isinstance(access_token, tuple) and access_token[0] == "acc-key"
    assert identity["username"] == "Alice"


def test_complete_login_raises_identity_error(monkeypatch):
    class FailingHandshaker(StubHandshaker):
        def identify(self, _access_token):
            raise RuntimeError("boom")

    class FailingMWOAuth(StubMWOAuth):
        def __init__(self):
            super().__init__()
            self.Handshaker = FailingHandshaker

    monkeypatch.setattr(oauth_helpers, "mwoauth", FailingMWOAuth())
    with pytest.raises(oauth_helpers.OAuthIdentityError):
        oauth_helpers.complete_login(("rk", "rs"), "x=1")
