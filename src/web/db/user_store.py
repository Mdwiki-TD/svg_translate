"""Persistence helpers for OAuth user credentials."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
except ModuleNotFoundError:  # pragma: no cover - dependency missing in some CI
    Fernet = None  # type: ignore[assignment]

    class InvalidToken(Exception):
        """Fallback InvalidToken exception used when cryptography is absent."""

from .db_class import Database
from .utils import _current_ts


@dataclass
class UserCredentials:
    """Decrypted OAuth credential bundle stored in the database."""

    user_id: str
    username: str
    access_token: str
    access_secret: str
    created_at: str
    updated_at: str
    last_used_at: str | None
    rotated_at: str | None

    def without_secrets(self) -> Dict[str, str]:
        """Return a representation safe for exposure to templates."""

        return {
            "user_id": self.user_id,
            "username": self.username,
        }

    def secrets(self) -> Dict[str, str]:
        """Return the sensitive token payload for internal use."""

        return {
            "access_token": self.access_token,
            "access_secret": self.access_secret,
        }

    def is_revoked(self) -> bool:
        """Return ``True`` when the stored credentials have been revoked."""

        return bool(self.rotated_at) or not (self.access_token and self.access_secret)


class UserTokenStore:
    """MySQL-backed store for OAuth access tokens with transparent encryption."""

    def __init__(self, db_data: Dict[str, str], encryption_key: str) -> None:
        if not encryption_key:
            raise ValueError("OAUTH_ENCRYPTION_KEY is required to initialise UserTokenStore")

        if Fernet is None:  # pragma: no cover - handled by explicit tests
            raise RuntimeError("cryptography is required to use UserTokenStore")

        key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        try:
            self.fernet = Fernet(key_bytes)
        except Exception as exc:  # pragma: no cover - validation branch
            raise ValueError("OAUTH_ENCRYPTION_KEY is not a valid Fernet key") from exc

        self.db = Database(db_data)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the ``user_tokens`` table if it does not already exist."""

        ddl = """
            CREATE TABLE IF NOT EXISTS user_tokens (
                user_id VARCHAR(255) PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                access_token VARBINARY(1024) NOT NULL,
                access_secret VARBINARY(1024) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                last_used_at DATETIME DEFAULT NULL,
                rotated_at DATETIME DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.db.execute_query_safe(ddl)

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def _encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode("utf-8"))

    def _decrypt(self, value: bytes) -> str:
        try:
            return self.fernet.decrypt(value).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Failed to decrypt stored OAuth token") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert_credentials(self, user_id: str, username: str, access_token: str, access_secret: str) -> None:
        """Insert or update a user's OAuth credentials."""

        now = _current_ts()
        encrypted_token = self._encrypt(access_token)
        encrypted_secret = self._encrypt(access_secret)

        self.db.execute_query_safe(
            """
            INSERT INTO user_tokens (
                user_id, username, access_token, access_secret, created_at, updated_at, last_used_at, rotated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                access_token = VALUES(access_token),
                access_secret = VALUES(access_secret),
                updated_at = VALUES(updated_at),
                last_used_at = VALUES(last_used_at),
                rotated_at = NULL
            """,
            [
                user_id,
                username,
                encrypted_token,
                encrypted_secret,
                now,
                now,
                now,
            ],
        )

    def get_user(self, user_id: str) -> Optional[UserCredentials]:
        """Fetch and decrypt a user's OAuth credentials."""

        rows = self.db.fetch_query_safe(
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
            [user_id],
        )
        if not rows:
            return None

        row = rows[0]
        return UserCredentials(
            user_id=row["user_id"],
            username=row["username"],
            access_token=self._decrypt(row["access_token"]),
            access_secret=self._decrypt(row["access_secret"]),
            created_at=str(row.get("created_at")),
            updated_at=str(row.get("updated_at")),
            last_used_at=str(row.get("last_used_at")) if row.get("last_used_at") else None,
            rotated_at=str(row.get("rotated_at")) if row.get("rotated_at") else None,
        )

    def mark_last_used(self, user_id: str) -> None:
        """Update the ``last_used_at`` timestamp for ``user_id``."""

        now = _current_ts()
        self.db.execute_query_safe(
            "UPDATE user_tokens SET last_used_at = %s WHERE user_id = %s",
            [now, user_id],
        )

    def revoke(self, user_id: str) -> None:
        """Rotate credentials for ``user_id`` and scrub stored secrets."""

        now = _current_ts()
        placeholder = self._encrypt("")
        self.db.execute_query_safe(
            """
            UPDATE user_tokens
            SET access_token = %s,
                access_secret = %s,
                updated_at = %s,
                last_used_at = %s,
                rotated_at = %s
            WHERE user_id = %s
            """,
            [placeholder, placeholder, now, now, now, user_id],
        )

    def purge_stale(self, *, max_age_days: int = 90) -> int:
        """Delete revoked or long-idle OAuth credentials.

        Args:
            max_age_days: Retain credentials that have been used within this
                window. Rows with ``rotated_at`` set are purged immediately.

        Returns:
            int: Number of deleted credential rows.
        """

        if max_age_days <= 0:
            raise ValueError("max_age_days must be positive")

        cutoff = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=max_age_days)
        ).strftime("%Y-%m-%d %H:%M:%S")

        deleted = self.db.execute_query_safe(
            """
            DELETE FROM user_tokens
            WHERE rotated_at IS NOT NULL
               OR COALESCE(last_used_at, updated_at, created_at) < %s
            """,
            [cutoff],
        )

        return int(deleted or 0)


__all__ = ["UserTokenStore", "UserCredentials"]
