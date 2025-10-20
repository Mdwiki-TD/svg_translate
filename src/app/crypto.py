"""Symmetric encryption helpers for storing OAuth secrets."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


if not settings.oauth_encryption_key:
    raise RuntimeError(
        "OAUTH_ENCRYPTION_KEY must be configured before using the crypto helpers"
    )

_fernet = Fernet(settings.oauth_encryption_key)


def encrypt_value(value: str) -> bytes:
    """Encrypt a UTF-8 string and return the raw Fernet token bytes."""

    return _fernet.encrypt(value.encode("utf-8"))


def decrypt_value(token: bytes) -> str:
    """Decrypt a Fernet token and return the UTF-8 string contents."""

    try:
        decrypted = _fernet.decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt stored token") from exc
    return decrypted.decode("utf-8")
