"""Symmetric encryption helpers for storing sensitive tokens."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from .config import FERNET_KEY


if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY is not configured")

_fernet = Fernet(FERNET_KEY)


def encrypt_text(plaintext: str) -> str:
    """Encrypt a UTF-8 string into a URL-safe token."""
    token = _fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str) -> str:
    """Decrypt a previously encrypted token back to a UTF-8 string."""
    try:
        plaintext = _fernet.decrypt(token.encode("utf-8"))
    except InvalidToken as exc:  # pragma: no cover - defensive guard
        raise ValueError("Invalid encrypted token") from exc
    return plaintext.decode("utf-8")
