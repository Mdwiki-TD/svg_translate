"""Utilities for managing administrator (coordinator) accounts."""

from __future__ import annotations

import logging
from typing import List, Optional

from ..config import settings
from ..db import has_db_config
from ..db.db_CoordinatorsDB import CoordinatorStore, CoordinatorRecord, CoordinatorsDB

logger = logging.getLogger(__name__)

_ADMINS_STORE: CoordinatorStore | None = None


def get_admins_db() -> CoordinatorStore:
    global _ADMINS_STORE

    if _ADMINS_STORE is None:
        if not has_db_config():
            raise RuntimeError(
                "Coordinator administration requires database configuration; no fallback store is available."
            )

        try:
            _ADMINS_STORE = CoordinatorsDB(settings.db_data)
        except Exception as exc:  # pragma: no cover - defensive guard for startup failures
            logger.exception("Failed to initialize MySQL coordinator store")
            raise RuntimeError("Unable to initialize coordinator store") from exc

    return _ADMINS_STORE


def _refresh_settings(store: Optional[CoordinatorStore] = None) -> List[CoordinatorRecord]:
    store = store or get_admins_db()
    records = store.admins_list()
    active = [record.username for record in records if record.is_active]
    object.__setattr__(settings, "admins", active)
    return records


def list_coordinators() -> List[CoordinatorRecord]:
    """Return all coordinators while keeping settings.admins in sync."""

    store = get_admins_db()

    return store.admins_list()


def add_coordinator(username: str) -> CoordinatorRecord:
    """Add a coordinator and refresh the runtime admin list."""

    store = get_admins_db()
    record = store.add(username)
    _refresh_settings(store)
    return record


def set_coordinator_active(coordinator_id: int, is_active: bool) -> CoordinatorRecord:
    """Toggle coordinator activity and refresh settings."""

    store = get_admins_db()
    record = store.set_active(coordinator_id, is_active)
    _refresh_settings(store)
    return record


def delete_coordinator(coordinator_id: int) -> CoordinatorRecord:
    """Delete a coordinator and refresh settings."""

    store = get_admins_db()
    record = store.delete(coordinator_id)
    _refresh_settings(store)
    return record


def set_store_for_testing(store: CoordinatorStore | None) -> None:
    """Override the coordinator store implementation (primarily for tests)."""

    global _ADMINS_STORE
    _ADMINS_STORE = store
    if store is not None:
        _refresh_settings(store)


__all__ = [
    "get_admins_db",
    "CoordinatorRecord",
    "CoordinatorStore",
    "CoordinatorsDB",
    "list_coordinators",
    "add_coordinator",
    "set_coordinator_active",
    "delete_coordinator",
    "set_store_for_testing",
]
