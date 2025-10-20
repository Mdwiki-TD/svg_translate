"""Utilities for accessing the authenticated MediaWiki user."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import session

from .db import get_user


def current_user() -> Optional[Dict[str, Any]]:
    """Return the current user record stored in the session, if any."""
    uid = session.get("uid")
    if not uid:
        return None
    try:
        user_id = int(uid)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return None
    return get_user(user_id)
