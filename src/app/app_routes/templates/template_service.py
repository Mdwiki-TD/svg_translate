"""Utilities for managing administrator (template) accounts."""

from __future__ import annotations

import logging
from typing import List

from ...config import settings
from ...db import has_db_config
from ...db.db_Templates import TemplateRecord, TemplatesDB

logger = logging.getLogger(__name__)

_TEMPLATE_STORE: TemplatesDB | None = None


def get_templates_db() -> TemplatesDB:
    global _TEMPLATE_STORE

    if _TEMPLATE_STORE is None:
        if not has_db_config():
            raise RuntimeError(
                "Template administration requires database configuration; no fallback store is available."
            )

        try:
            _TEMPLATE_STORE = TemplatesDB(settings.db_data)
        except Exception as exc:  # pragma: no cover - defensive guard for startup failures
            logger.exception("Failed to initialize MySQL template store")
            raise RuntimeError("Unable to initialize template store") from exc

    return _TEMPLATE_STORE


def active_templates() -> list:
    """Return all templates while keeping settings.admins in sync."""

    store = get_templates_db()

    return [u.username for u in store.list() if u.is_active]


def list_templates() -> List[TemplateRecord]:
    """Return all templates while keeping settings.admins in sync."""

    store = get_templates_db()

    coords = store.list()
    return coords


def add_template(username: str) -> TemplateRecord:
    """Add a template and refresh the runtime admin list."""

    store = get_templates_db()
    record = store.add(username)

    return record


def set_template_active(template_id: int, is_active: bool) -> TemplateRecord:
    """Toggle template activity and refresh settings."""

    store = get_templates_db()
    record = store.set_active(template_id, is_active)

    return record


def delete_template(template_id: int) -> TemplateRecord:
    """Delete a template and refresh settings."""

    store = get_templates_db()
    record = store.delete(template_id)

    return record


__all__ = [
    "get_templates_db",
    "active_templates",
    "TemplateRecord",
    "TemplatesDB",
    "list_templates",
    "add_template",
    "set_template_active",
    "delete_template",
]
