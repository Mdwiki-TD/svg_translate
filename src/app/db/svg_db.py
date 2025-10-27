"""Compatibility shim exposing legacy helpers built atop :class:`Database`."""

from __future__ import annotations

import atexit
import logging
from typing import Any, Optional

from ..config import settings
from .. import svg_config
from .db_class import Database

db_data = svg_config.db_data
_db: Database | None = None
_shutdown_hook_registered = False

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
        _ensure_shutdown_hook()
    return _db


def close_cached_db() -> None:
    """Release the cached :class:`Database` instance when it is no longer needed.

    The connection is intentionally kept alive for the lifetime of the process so
    that sequential requests can reuse it.  :func:`close_cached_db` is registered
    via ``atexit`` (triggered the first time :func:`get_db` is called) so that the
    handle is cleaned up automatically when the service shuts down.  Tests or
    manual callers can still invoke this helper explicitly to dispose of the
    cached connection earlier in the lifecycle.
    """
    global _db
    if _db is not None:
        _db.close()
        _db = None


def _ensure_shutdown_hook() -> None:
    """Register an ``atexit`` hook to clean up the cached database connection."""

    global _shutdown_hook_registered
    if not _shutdown_hook_registered:
        atexit.register(close_cached_db)
        _shutdown_hook_registered = True


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
