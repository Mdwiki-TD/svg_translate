"""Focused unit tests for routes_utils helpers (pure functions)."""
from datetime import datetime

from src.app.routes_utils import (
    get_error_message,
    _format_timestamp,
    order_stages,
    format_task,
    load_auth_payload,
)


def test_get_error_message_known_and_unknown():
    assert get_error_message("task-active") == "A task for this title is already in progress."
    assert get_error_message("not-found") == "Task not found."
    assert get_error_message(None) == ""
    assert get_error_message("some-other") == "some-other"


def test_format_timestamp_variants():
    dt = datetime(2024, 1, 2, 3, 4, 5)
    disp, key = _format_timestamp(dt)
    assert disp == "2024-01-02 03:04:05"
    assert key.startswith("2024-01-02T03:04:05")

    disp2, key2 = _format_timestamp("2024-01-02 03:04:05")
    assert disp2 == "2024-01-02 03:04:05"
    assert key2.startswith("2024-01-02T03:04:05")

    disp3, key3 = _format_timestamp(None)
    assert disp3 == ""
    assert key3 == ""


def test_order_stages_and_format_task():
    stages = {
        "download": {"number": 5, "status": "Completed", "message": "done"},
        "text": {"number": 2, "status": "Completed"},
    }
    ordered = order_stages(stages)
    assert [name for name, _ in ordered] == ["text", "download"]

    task = {
        "id": "T1",
        "title": "Title",
        "status": "Completed",
        "results": {
            "files_to_upload_count": 3,
            "new_translations_count": 2,
            "total_files": 5,
            "injects_result": {"nested_files": 1},
        },
        "created_at": "2024-01-02 03:04:05",
        "updated_at": "2024-01-02 03:05:00",
        "username": "tester",
        "stages": stages,
    }
    ft = format_task(task)
    assert ft["files_to_upload_count"] == 3
    assert ft["new_translations_count"] == 2
    assert ft["nested_files"] == 1
    assert ft["created_at_display"] == "2024-01-02 03:04:05"
    assert ft["username"] == "tester"


def test_load_auth_payload_happy_path():
    class U:
        user_id = 9
        username = "user9"
        access_token = "ak"  # noqa: S105
        access_secret = "as"  # noqa: S105

    payload = load_auth_payload(U())
    assert payload["id"] == 9
    assert payload["username"] == "user9"
    assert payload["access_token"] == "ak"  # noqa: S105
    assert payload["access_secret"] == "as"  # noqa: S105