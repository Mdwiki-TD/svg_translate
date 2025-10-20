"""A simple, insecure Fernet stub for unit tests."""

from __future__ import annotations

import base64


class InvalidToken(Exception):
    pass


class Fernet:
    def __init__(self, key: str | bytes):
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        if not key:
            raise ValueError("Fernet key must be non-empty")
        self._key = key

    @staticmethod
    def generate_key() -> bytes:  # pragma: no cover - helper
        raw = b"test-fernet-key-for-compat-tests-1234"
        return base64.urlsafe_b64encode(raw)

    def encrypt(self, data: bytes) -> bytes:
        payload = f"{self._key}:{data.decode('utf-8')}".encode("utf-8")
        return base64.urlsafe_b64encode(payload)

    def decrypt(self, token: bytes) -> bytes:
        try:
            payload = base64.urlsafe_b64decode(token)
        except Exception as exc:  # pragma: no cover - defensive
            raise InvalidToken("Invalid token encoding") from exc
        try:
            key, value = payload.decode("utf-8").split(":", 1)
        except ValueError as exc:  # pragma: no cover - defensive
            raise InvalidToken("Invalid token structure") from exc
        if key != self._key:
            raise InvalidToken("Key mismatch")
        return value.encode("utf-8")
