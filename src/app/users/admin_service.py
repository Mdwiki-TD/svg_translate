"""Utilities for managing administrator (coordinator) accounts."""

from __future__ import annotations

import logging
from typing import List

from ..config import settings
from ..db import has_db_config
from ..db.db_CoordinatorsDB import CoordinatorRecord, CoordinatorsDB

logger = logging.getLogger("svg_translate")

_ADMINS_STORE: CoordinatorsDB | None = None


def get_admins_db() -> CoordinatorsDB:
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


def active_coordinators() -> list:
    """Return all coordinators while keeping settings.admins in sync."""

    store = get_admins_db()

    return [u.username for u in store.list() if u.is_active]


def list_coordinators() -> List[CoordinatorRecord]:
    """Return all coordinators while keeping settings.admins in sync."""

    store = get_admins_db()

    coords = store.list()
    return coords


def add_coordinator(username: str) -> CoordinatorRecord:
    """Add a coordinator."""

    store = get_admins_db()
    record = store.add(username)

    return record


def set_coordinator_active(coordinator_id: int, is_active: bool) -> CoordinatorRecord:
    """Toggle coordinator activity and refresh settings."""

    store = get_admins_db()
    record = store.set_active(coordinator_id, is_active)

    return record


def delete_coordinator(coordinator_id: int) -> CoordinatorRecord:
    """Delete a coordinator and refresh settings."""

    store = get_admins_db()
    record = store.delete(coordinator_id)

    return record


__all__ = [
    "get_admins_db",
    "active_coordinators",
    "CoordinatorRecord",
    "CoordinatorsDB",
    "list_coordinators",
    "add_coordinator",
    "set_coordinator_active",
    "delete_coordinator",
]
