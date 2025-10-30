"""Utilities for managing administrator (template) accounts."""

from __future__ import annotations

import logging
from typing import List

from .config import settings
from .db import has_db_config
from .db.db_Templates import TemplateRecord, TemplatesDB

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


def list_templates() -> List[TemplateRecord]:
    """Return all templates while keeping settings.admins in sync."""

    store = get_templates_db()

    coords = store.list()
    return coords


def add_template(title: str, main_file: str) -> TemplateRecord:
    """Add a template."""

    store = get_templates_db()
    record = store.add(title, main_file)

    return record


def add_or_update_template(title: str, main_file: str) -> TemplateRecord:
    """Add a template."""

    store = get_templates_db()
    record = store.add_or_update(title, main_file)

    return record


def update_template(template_id: int, title: str, main_file: str) -> TemplateRecord:
    """Update template."""

    store = get_templates_db()
    record = store.update(template_id, title, main_file)

    return record


def delete_template(template_id: int) -> TemplateRecord:
    """Delete a template."""

    store = get_templates_db()
    record = store.delete(template_id)

    return record


__all__ = [
    "get_templates_db",
    "TemplateRecord",
    "TemplatesDB",
    "list_templates",
    "add_template",
    "update_template",
    "delete_template",
]
