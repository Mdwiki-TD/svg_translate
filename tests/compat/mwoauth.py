"""Lightweight stub of the mwoauth package for test execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class RequestToken(tuple):
    key: str
    secret: str

    def __new__(cls, key: str, secret: str):
        return tuple.__new__(cls, (key, secret))


@dataclass
class AccessToken(tuple):
    key: str
    secret: str

    def __new__(cls, key: str, secret: str):
        return tuple.__new__(cls, (key, secret))


class Handshaker:
    def __init__(self, *_, **__):
        self._token = RequestToken("request-key", "request-secret")
        self._access = AccessToken("access-key", "access-secret")

    def initiate(self, callback: str) -> Tuple[str, RequestToken]:  # pragma: no cover - trivial
        return "https://example.org/oauth", self._token

    def complete(self, request_token: RequestToken, oauth_verifier: str) -> AccessToken:  # pragma: no cover - trivial
        return self._access

    def identify(self, access_token: AccessToken) -> Dict[str, str]:  # pragma: no cover - trivial
        return {"username": "TestUser", "sub": "1"}
