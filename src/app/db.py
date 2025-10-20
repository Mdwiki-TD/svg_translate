"""Database helpers for storing OAuth user credentials."""

from __future__ import annotations

from typing import Any, Dict, Optional

from web.db.db_class import Database

from svg_config import db_data

_db: Database | None = None


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(db_data)
    return _db


def ensure_user_table() -> None:
    """Create the users table if it does not already exist."""
    db = _get_db()
    db.execute_query(
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            token_enc TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
    )
    db.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """
    )


def upsert_user(*, user_id: int, username: str, token_enc: str) -> None:
    """Insert or update a user record with the encrypted OAuth token."""
    db = _get_db()
    db.execute_query(
        """
        INSERT INTO users (id, username, token_enc)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            token_enc = VALUES(token_enc)
        """,
        (user_id, username, token_enc),
    )


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a user record by numeric identifier."""
    db = _get_db()
    rows = db.fetch_query("SELECT * FROM users WHERE id = %s", (user_id,))
    return rows[0] if rows else None
