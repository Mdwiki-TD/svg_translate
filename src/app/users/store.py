"""Persistence helpers for storing encrypted OAuth tokens."""

from __future__ import annotations

import logging
import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..config import settings

# from ..svg_config import db_data
from ..db.db_class import Database
from ..crypto import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

_db: Database | None = None


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(settings.db_data)
    return _db


def close_cached_db() -> None:
    """Close the cached :class:`Database` instance if it has been initialized."""

    if _db is not None:
        _db.close()


def _current_ts() -> str:
    # Store in UTC. MySQL DATETIME has no TZ; keep application-level UTC.
    """
    Return the current UTC timestamp formatted for MySQL DATETIME.

    Returns:
        A string of the current UTC time in the format "YYYY-MM-DD HH:MM:SS".
    """
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _coerce_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    raise TypeError("Expected bytes-compatible value for encrypted token")


def mark_token_used(user_id: int) -> None:
    """Update the last-used timestamp for the given user token."""

    db = _get_db()
    try:
        db.execute_query(
            "UPDATE user_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE user_id = %s",
            (user_id,),
        )
    except Exception:
        logger.exception("Failed to update last_used_at for user %s", user_id)


@dataclass
class UserTokenRecord:
    """Decrypted OAuth credential bundle stored in the database."""

    user_id: int
    username: str
    access_token: bytes
    access_secret: bytes
    created_at: Any | None = None
    updated_at: Any | None = None
    last_used_at: Any | None = None
    rotated_at: Any | None = None

    def decrypted(self) -> tuple[str, str]:
        """Return the decrypted access token and secret."""

        access_key = decrypt_value(self.access_token)
        access_secret = decrypt_value(self.access_secret)
        mark_token_used(self.user_id)
        return access_key, access_secret


def ensure_user_token_table() -> None:
    """Create the user_tokens table if it does not already exist."""

    db = _get_db()
    db.execute_query_safe(
        """
        CREATE TABLE IF NOT EXISTS user_tokens (
            user_id INT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            access_token VARBINARY(1024) NOT NULL,
            access_secret VARBINARY(1024) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_used_at DATETIME DEFAULT NULL,
            rotated_at DATETIME DEFAULT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Ensure username index exists
    existing_idx = db.fetch_query_safe(
        "SHOW INDEX FROM user_tokens WHERE Key_name = %s",
        ("idx_user_tokens_username",),
    )
    if not existing_idx:
        db.execute_query_safe(
            """
            CREATE INDEX /*IF NOT EXISTS*/ idx_user_tokens_username ON user_tokens(username)
            """
        )


def upsert_user_token(*, user_id: int, username: str, access_key: str, access_secret: str) -> None:
    """Insert or update the encrypted OAuth credentials for a user."""

    db = _get_db()
    now = _current_ts()
    encrypted_token = encrypt_value(access_key)
    encrypted_secret = encrypt_value(access_secret)
    return db.execute_query_safe(
        """
            INSERT INTO user_tokens (
                user_id,
                username,
                access_token,
                access_secret,
                created_at,
                updated_at,
                last_used_at,
                rotated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                access_token = VALUES(access_token),
                access_secret = VALUES(access_secret),
                updated_at = VALUES(updated_at),
                last_used_at = VALUES(last_used_at),
                rotated_at = CURRENT_TIMESTAMP
            """,
        (
            user_id,
            username,
            encrypted_token,
            encrypted_secret,
            now,
            now,
            now,
        ),
    )


def get_user_token(user_id: str | int) -> Optional[UserTokenRecord]:
    """Fetch the encrypted OAuth credentials for a user."""
    user_id = int(user_id) if isinstance(user_id, str) else user_id

    db = _get_db()
    rows: list[Dict[str, Any]] = db.fetch_query_safe(
        """
        SELECT
            user_id,
            username,
            access_token,
            access_secret,
            created_at,
            updated_at,
            last_used_at,
            rotated_at
        FROM user_tokens
        WHERE user_id = %s
        """,
        (user_id,),
    )
    if not rows:
        return None

    row = rows[0]
    return UserTokenRecord(
        user_id=row["user_id"],
        username=row["username"],
        access_token=_coerce_bytes(row["access_token"]),
        access_secret=_coerce_bytes(row["access_secret"]),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        last_used_at=row.get("last_used_at"),
        rotated_at=row.get("rotated_at"),
    )


def delete_user_token(user_id: int) -> None:
    """Remove the stored OAuth credentials for the given user id."""

    db = _get_db()
    db.execute_query_safe("DELETE FROM user_tokens WHERE user_id = %s", (user_id,))
