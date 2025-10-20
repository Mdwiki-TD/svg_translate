"""Persistence helpers for OAuth user credentials."""

from __future__ import annotations

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

    def as_dict(self, include_secrets: bool = False) -> Dict[str, str]:
        """Return a dictionary representation suitable for templating."""

        data = {
            "user_id": self.user_id,
            "username": self.username,
        }
        if include_secrets:
            data.update(
                {
                    "access_token": self.access_token,
                    "access_secret": self.access_secret,
                }
            )
        return data


class UserTokenStore:
    """MySQL-backed store for OAuth access tokens with transparent encryption."""

    def __init__(self, db_data: Dict[str, str], encryption_key: str) -> None:
        if not encryption_key:
            raise ValueError("OAUTH_ENCRYPTION_KEY is required to initialise UserTokenStore")

        if Fernet is None:  # pragma: no cover - handled by explicit tests
            raise RuntimeError("cryptography is required to use UserTokenStore")

        self.db = Database(db_data)
        self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the ``user_tokens`` table if it does not already exist."""

        ddl = """
            CREATE TABLE IF NOT EXISTS user_tokens (
                user_id VARCHAR(255) PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                access_token VARBINARY(1024) NOT NULL,
                access_secret VARBINARY(1024) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
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
        self.db.execute_query_safe(
            """
            INSERT INTO user_tokens (
                user_id, username, access_token, access_secret, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                access_token = VALUES(access_token),
                access_secret = VALUES(access_secret),
                updated_at = VALUES(updated_at)
            """,
            [
                user_id,
                username,
                self._encrypt(access_token),
                self._encrypt(access_secret),
                now,
                now,
            ],
        )

    def get_user(self, user_id: str) -> Optional[UserCredentials]:
        """Fetch and decrypt a user's OAuth credentials."""

        rows = self.db.fetch_query_safe(
            """
            SELECT user_id, username, access_token, access_secret, created_at, updated_at
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
        )

    def delete_user(self, user_id: str) -> None:
        """Remove a user's credentials from the store."""

        self.db.execute_query_safe("DELETE FROM user_tokens WHERE user_id = %s", [user_id])


__all__ = ["UserTokenStore", "UserCredentials"]
