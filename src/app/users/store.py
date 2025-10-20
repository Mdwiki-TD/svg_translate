"""Persistence helpers for storing encrypted OAuth tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from svg_config import db_data
from web.db.db_class import Database

from ..crypto import decrypt_value, encrypt_value

_db: Database | None = None


def _coerce_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    raise TypeError("Expected bytes-compatible value for encrypted token")


@dataclass
class UserTokenRecord:
    user_id: int
    username: str
    access_token_enc: bytes
    access_secret_enc: bytes
    created_at: Any | None = None
    updated_at: Any | None = None

    def decrypted(self) -> tuple[str, str]:
        """Return the decrypted access token and secret."""

        access_key = decrypt_value(self.access_token_enc)
        access_secret = decrypt_value(self.access_secret_enc)
        return access_key, access_secret


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(db_data)
    return _db


def ensure_user_token_table() -> None:
    """Create the user_tokens table if it does not already exist."""

    db = _get_db()
    db.execute_query(
        """
        CREATE TABLE IF NOT EXISTS user_tokens (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            access_token_enc VARBINARY(255) NOT NULL,
            access_secret_enc VARBINARY(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """,
    )
    db.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_user_tokens_username ON user_tokens(username)
        """
    )


def upsert_user_token(*, user_id: int, username: str, access_key: str, access_secret: str) -> None:
    """Insert or update the encrypted OAuth credentials for a user."""

    db = _get_db()
    db.execute_query(
        """
        INSERT INTO user_tokens (user_id, username, access_token_enc, access_secret_enc)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            access_token_enc = VALUES(access_token_enc),
            access_secret_enc = VALUES(access_secret_enc)
        """,
        (
            user_id,
            username,
            encrypt_value(access_key),
            encrypt_value(access_secret),
        ),
    )


def delete_user_token(user_id: int) -> None:
    """Remove the stored OAuth credentials for the given user id."""

    db = _get_db()
    db.execute_query("DELETE FROM user_tokens WHERE user_id = %s", (user_id,))


def get_user_token(user_id: int) -> Optional[UserTokenRecord]:
    """Fetch the encrypted OAuth credentials for a user."""

    db = _get_db()
    rows: list[Dict[str, Any]] = db.fetch_query(
        "SELECT * FROM user_tokens WHERE user_id = %s", (user_id,)
    )
    if not rows:
        return None
    row = rows[0]
    return UserTokenRecord(
        user_id=row["user_id"],
        username=row["username"],
        access_token_enc=_coerce_bytes(row["access_token_enc"]),
        access_secret_enc=_coerce_bytes(row["access_secret_enc"]),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
