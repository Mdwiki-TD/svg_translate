"""Compatibility shim exposing legacy helpers built atop :class:`Database`."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..config import settings
from .db_class import Database

_db: Database | None = None

logger = logging.getLogger(__name__)


def has_db_config() -> bool:
    """Return ``True`` when database connection details are configured."""

    db_settings = settings.db_data or {}
    return bool(db_settings.get("host") or db_settings.get("db_connect_file"))


def get_db() -> Database:
    """Return a lazily-instantiated :class:`Database` using ``db_data``."""
    global _db

    if not has_db_config():
        logger.error("MySQL configuration is not available for the user token store.")

    if _db is None:
        _db = Database(settings.db_data)
    return _db


def close_cached_db() -> None:
    """Close the cached :class:`Database` instance if it has been initialized."""
    global _db
    if _db is not None:
        _db.close()
        _db = None


def execute_query(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.execute_query` for backwards compatibility."""

    with get_db() as db:
        return db.execute_query(sql_query, params)


def fetch_query(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.fetch_query` for backwards compatibility."""

    with get_db() as db:
        return db.fetch_query(sql_query, params)


def execute_query_safe(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.execute_query_safe` for backwards compatibility."""

    with get_db() as db:
        return db.execute_query_safe(sql_query, params)


def fetch_query_safe(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.fetch_query_safe` for backwards compatibility."""

    with get_db() as db:
        return db.fetch_query_safe(sql_query, params)


__all__ = [
    "get_db",
    "has_db_config",
    "close_cached_db",
    "execute_query",
    "fetch_query",
    "execute_query_safe",
    "fetch_query_safe",
]
