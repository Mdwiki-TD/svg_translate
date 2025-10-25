"""Compatibility shim exposing legacy helpers built atop :class:`Database`."""

from __future__ import annotations

from typing import Any, Optional

from ..config import settings

from app import svg_config
from .db_class import Database

db_data = svg_config.db_data

_db: Database | None = None


def _get_db() -> Database:
    """Return a lazily-instantiated :class:`Database` using ``db_data``."""
    global _db
    if _db is None:
        _db = Database(settings.db_data)
    return _db


def execute_query(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.execute_query` for backwards compatibility."""

    with _get_db() as db:
        return db.execute_query(sql_query, params)


def fetch_query(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.fetch_query` for backwards compatibility."""

    with _get_db() as db:
        return db.fetch_query(sql_query, params)


def execute_query_safe(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.execute_query_safe` for backwards compatibility."""

    with _get_db() as db:
        return db.execute_query_safe(sql_query, params)


def fetch_query_safe(sql_query: str, params: Optional[Any] = None):
    """Proxy :meth:`Database.fetch_query_safe` for backwards compatibility."""

    with _get_db() as db:
        return db.fetch_query_safe(sql_query, params)


__all__ = [
    "Database",
    "db_data",
    "execute_query",
    "fetch_query",
    "execute_query_safe",
    "fetch_query_safe",
]
