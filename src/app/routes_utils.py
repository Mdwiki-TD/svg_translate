#
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def load_auth_payload(user: Any | None):
    auth_payload: Dict[str, Any] = {}
    if user:
        # returns (access_key, access_secret) and marks token used
        access_key, access_secret = user.access_token, user.access_secret

        # if hasattr(user, "decrypted"): access_key, access_secret = user.decrypted()

        auth_payload = {
            "id": user.user_id,
            "username": user.username,
            "access_token": access_key,
            "access_secret": access_secret,
        }
    return auth_payload


def get_error_message(error_code: str | None) -> str:
    if not error_code:
        return ""
    # ---
    messages = {
        "task-active": "A task for this title is already in progress.",
        "not-found": "Task not found.",
        "task-create-failed": "Task creation failed.",
    }
    # ---
    return messages.get(error_code, error_code)


def _format_timestamp(value: datetime | str | None) -> tuple[str, str]:
    """
    Format a timestamp value for user display and provide a sortable ISO-style key.

    Parameters:
        value (datetime | str | None): The timestamp to format. May be a datetime, a string (ISO format or "%Y-%m-%d %H:%M:%S"), or None.

    Returns:
        tuple[str, str]: A pair (display, sort_key).
            - display: human-readable timestamp in "YYYY-MM-DD HH:MM:SS", an empty string if `value` is None, or the original string if it could not be parsed.
            - sort_key: an ISO-format timestamp suitable for sorting, an empty string if `value` is None, or the original string if it could not be parsed.
    """
    if not value:
        return "", ""

    dt = None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            # First, try parsing as an ISO 8601 format string.
            dt = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            try:
                # If that fails, try the specific "%Y-%m-%d %H:%M:%S" format.
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                # If both fail, dt remains None.
                pass

    if not dt:
        return str(value), str(value)

    display = dt.strftime("%Y-%m-%d %H:%M:%S")
    sort_key = dt.isoformat()

    return display, sort_key


def _format_task(task: dict) -> dict:
    """Formats a task dictionary for the tasks list view."""
    results = task.get("results") or {}
    injects = results.get("injects_result") or {}

    created_display, created_sort = _format_timestamp(task.get("created_at"))
    updated_display, updated_sort = _format_timestamp(task.get("updated_at"))

    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "status": task.get("status"),
        "files_to_upload_count": results.get("files_to_upload_count", 0),
        "new_translations_count": results.get("new_translations_count", 0),
        "total_files": results.get("total_files", 0),
        "nested_files": injects.get("nested_files", 0),
        "created_at_display": created_display,
        "created_at_sort": created_sort,
        "updated_at_display": updated_display,
        "updated_at_sort": updated_sort,
        "username": task.get("username", "")
    }


def _order_stages(stages: Dict[str, Any] | None) -> List[tuple[str, Dict[str, Any]]]:
    if not stages:
        return []
    ordered = [
        (name, data)
        for name, data in stages.items()
        if isinstance(data, dict)
    ]
    ordered.sort(key=lambda item: item[1].get("number", 0))
    return ordered
