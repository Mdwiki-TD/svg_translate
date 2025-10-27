"""Utilities for managing administrator (coordinator) accounts."""

from __future__ import annotations

import logging
import pymysql
from typing import Any, Iterable, List, Optional

from ..config import settings
from ..db import Database, has_db_config
from .admin_service_utils import CoordinatorStore, CoordinatorRecord
from .admin_service_in_memory import InMemoryCoordinatorStore

logger = logging.getLogger(__name__)


class MySQLCoordinatorStore(CoordinatorStore):
    """MySQL-backed coordinator persistence using the shared Database helper."""

    def __init__(self, db_data: dict[str, Any]):
        self.db = Database(db_data)
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.db.execute_query_safe(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    def _row_to_record(self, row: dict[str, Any]) -> CoordinatorRecord:
        return CoordinatorRecord(
            id=int(row["id"]),
            username=row["username"],
            is_active=bool(row.get("is_active")),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _fetch_by_id(self, coordinator_id: int) -> CoordinatorRecord:
        rows = self.db.fetch_query_safe(
            """
            SELECT id, username, is_active, created_at, updated_at
            FROM admin_users
            WHERE id = %s
            """,
            (coordinator_id,),
        )
        if not rows:
            raise LookupError(f"Coordinator id {coordinator_id} was not found")
        return self._row_to_record(rows[0])

    def _fetch_by_username(self, username: str) -> CoordinatorRecord:
        rows = self.db.fetch_query_safe(
            """
            SELECT id, username, is_active, created_at, updated_at
            FROM admin_users
            WHERE username = %s
            """,
            (username,),
        )
        if not rows:
            raise LookupError(f"Coordinator {username!r} was not found")
        return self._row_to_record(rows[0])

    def seed(self, usernames: Iterable[str]) -> None:
        clean_usernames = [name.strip() for name in usernames if name and name.strip()]
        if not clean_usernames:
            return

        placeholders = ", ".join(["%s"] * len(clean_usernames))
        existing_rows = self.db.fetch_query_safe(
            f"SELECT username FROM admin_users WHERE username IN ({placeholders})",
            tuple(clean_usernames),
        )
        existing = {row["username"] for row in existing_rows}
        for username in clean_usernames:
            if username in existing:
                continue
            self.db.execute_query_safe(
                "INSERT INTO admin_users (username, is_active) VALUES (%s, 1)",
                (username,),
            )

    def list(self) -> List[CoordinatorRecord]:
        rows = self.db.fetch_query_safe(
            """
            SELECT id, username, is_active, created_at, updated_at
            FROM admin_users
            ORDER BY id ASC
            """
        )
        return [self._row_to_record(row) for row in rows]

    def add(self, username: str) -> CoordinatorRecord:
        username = username.strip()
        if not username:
            raise ValueError("Username is required")

        try:
            # Use execute_query to allow exception to propagate
            self.db.execute_query(
                "INSERT INTO admin_users (username, is_active) VALUES (%s, 1)",
                (username,),
            )
        except pymysql.err.IntegrityError:
            # This assumes a UNIQUE constraint on the username column
            raise ValueError(f"Coordinator '{username}' already exists") from None

        return self._fetch_by_username(username)

    def set_active(self, coordinator_id: int, is_active: bool) -> CoordinatorRecord:
        _ = self._fetch_by_id(coordinator_id)
        self.db.execute_query_safe(
            "UPDATE admin_users SET is_active = %s WHERE id = %s",
            (1 if is_active else 0, coordinator_id),
        )
        return self._fetch_by_id(coordinator_id)

    def delete(self, coordinator_id: int) -> CoordinatorRecord:
        record = self._fetch_by_id(coordinator_id)
        self.db.execute_query_safe(
            "DELETE FROM admin_users WHERE id = %s",
            (coordinator_id,),
        )
        return record


_STORE: CoordinatorStore | None = None


def _ensure_store() -> CoordinatorStore:
    global _STORE

    if _STORE is None:
        if has_db_config():
            try:
                _STORE = MySQLCoordinatorStore(settings.db_data)
            except Exception:  # pragma: no cover - defensive guard for startup failures
                logger.exception("Failed to initialize MySQL coordinator store")  # ; falling back to in-memory store
                # _STORE = InMemoryCoordinatorStore()
        # else:
            # _STORE = InMemoryCoordinatorStore()

            if _STORE:
                # _STORE.seed(settings.admins)
                _refresh_settings(_STORE)

    return _STORE


def _refresh_settings(store: Optional[CoordinatorStore] = None) -> List[CoordinatorRecord]:
    """
    TODO:
    The _refresh_settings function modifies the global settings.admins list at runtime. The settings object is intended to be a source of static configuration and is even defined as a frozen dataclass. Modifying it at runtime, especially to reflect database state, is a significant design issue.

    More critically, this creates a race condition. The admin_required decorator reads from settings.admins without any locking, while this function (and others that call it) writes to it. This can lead to inconsistent state and incorrect authorization decisions under concurrent load.

    A better approach would be to:

    Keep settings.admins for initial, configuration-defined admins only.
    Create a separate, thread-safe mechanism for checking if a user is a dynamic admin (from the database). This could be a function like is_admin(username) that checks the database, perhaps with its own caching layer protected by a lock.
    Update admin_required to use this new function in addition to (or instead of) settings.admins.
    This is a high-priority issue as it affects the correctness of the application's authorization logic.
    """
    store = store or _ensure_store()
    records = store.list()
    active = [record.username for record in records if record.is_active]
    object.__setattr__(settings, "admins", active)
    return records


def initialize_coordinators() -> None:
    """Ensure the backing store exists and synchronize settings.admins."""

    if not has_db_config():  # pragma: no cover - exercised indirectly in tests
        return

    _refresh_settings()


def list_coordinators() -> List[CoordinatorRecord]:
    """Return all coordinators while keeping settings.admins in sync."""

    return _refresh_settings()


def add_coordinator(username: str) -> CoordinatorRecord:
    """Add a coordinator and refresh the runtime admin list."""

    store = _ensure_store()
    record = store.add(username)
    _refresh_settings(store)
    return record


def set_coordinator_active(coordinator_id: int, is_active: bool) -> CoordinatorRecord:
    """Toggle coordinator activity and refresh settings."""

    store = _ensure_store()
    record = store.set_active(coordinator_id, is_active)
    _refresh_settings(store)
    return record


def delete_coordinator(coordinator_id: int) -> CoordinatorRecord:
    """Delete a coordinator and refresh settings."""

    store = _ensure_store()
    record = store.delete(coordinator_id)
    _refresh_settings(store)
    return record


def set_store_for_testing(store: CoordinatorStore | None) -> None:
    """Override the coordinator store implementation (primarily for tests)."""

    global _STORE
    _STORE = store
    if store is not None:
        _refresh_settings(store)


__all__ = [
    "CoordinatorRecord",
    "CoordinatorStore",
    "MySQLCoordinatorStore",
    "InMemoryCoordinatorStore",
    "initialize_coordinators",
    "list_coordinators",
    "add_coordinator",
    "set_coordinator_active",
    "delete_coordinator",
    "set_store_for_testing",
]
