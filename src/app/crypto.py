"""Symmetric encryption helpers for storing OAuth secrets."""

from __future__ import annotations
import os

import threading

from cryptography.fernet import Fernet, InvalidToken

OAUTH_ENCRYPTION_KEY = os.getenv("OAUTH_ENCRYPTION_KEY", "")

_fernet: Fernet | None = None
_fernet_lock = threading.Lock()


def _require_fernet() -> Fernet:
    global _fernet

    if _fernet is not None:
        return _fernet

    if not OAUTH_ENCRYPTION_KEY:
        raise RuntimeError(
            "OAUTH_ENCRYPTION_KEY must be configured before using the crypto helpers"
        )

    with _fernet_lock:
        if _fernet is not None:
            return _fernet

        key_bytes = (
            OAUTH_ENCRYPTION_KEY.encode()
            if isinstance(OAUTH_ENCRYPTION_KEY, str)
            else OAUTH_ENCRYPTION_KEY
        )

        try:
            _fernet = Fernet(key_bytes)
        except ValueError as exc:  # pragma: no cover - invalid configuration
            raise RuntimeError(
                "OAUTH_ENCRYPTION_KEY must be a 32-byte urlsafe base64-encoded string"
            ) from exc

    return _fernet


def encrypt_value(value: str) -> bytes:
    """Encrypt a UTF-8 string and return the raw Fernet token bytes."""

    return _require_fernet().encrypt(value.encode("utf-8"))


def decrypt_value(token: bytes) -> str:
    """Decrypt a Fernet token and return the UTF-8 string contents."""

    try:
        decrypted = _require_fernet().decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt stored token") from exc
    return decrypted.decode("utf-8")
