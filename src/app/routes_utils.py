#
from __future__ import annotations

from collections import namedtuple
from datetime import datetime
import logging
from typing import Any, Dict, List
from .svg_config import DISABLE_UPLOADS

logger = logging.getLogger(__name__)


def load_auth_payload(user):
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


def parse_args(request_form) -> Any:
    Args = namedtuple(
        "Args",
        [
            "titles_limit",
            "overwrite",
            "upload",
            "ignore_existing_task",
            "manual_main_title",
        ],
    )
    # ---
    upload = False
    # ---
    if DISABLE_UPLOADS != "1":
        upload = bool(request_form.get("upload"))
    # ---
    manual_main_title = request_form.get("manual_main_title", "")
    if manual_main_title:
        manual_main_title = manual_main_title.strip()
        if manual_main_title.lower().startswith("file:"):
            manual_main_title = manual_main_title.split(":", 1)[1].strip()
        if not manual_main_title:
            manual_main_title = None
    else:
        manual_main_title = None

    return Args(
        titles_limit=request_form.get("titles_limit", 1000, type=int),
        overwrite=bool(request_form.get("overwrite")),
        ignore_existing_task=bool(request_form.get("ignore_existing_task")),
        upload=upload,
        manual_main_title=manual_main_title,
    )


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
        for fmt in (None, "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.fromisoformat(value) if fmt is None else datetime.strptime(value, fmt)
                break
            except (TypeError, ValueError):
                continue

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
