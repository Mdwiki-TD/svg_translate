"""Upload task helpers with progress callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

import logging
from tqdm import tqdm

from .upload.upload_bot import upload_file

from ..users.store import mark_token_used
from ..wiki_client import build_upload_site

from .db.task_store_pymysql import TaskStorePyMysql

logger = logging.getLogger(__name__)
PerFileCallback = Optional[Callable[[int, int, Path, str], None]]


def _coerce_encrypted(value: object) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, str):
        return value.encode("utf-8")
    return None


def start_upload(
    files_to_upload: Dict[str, Dict[str, object]],
    main_title_link: str,
    site,
    stages,
    message_updater: PerFileCallback = None,
):
    """Upload files to Wikimedia Commons using an authenticated mwclient site."""

    done = 0
    not_done = 0
    no_changes = 0
    errors = []

    items = list(files_to_upload.items())
    total = len(items)

    if getattr(site, "logged_in", False):
        username = getattr(site, "username", "")
        if username:
            logger.debug(f"<<yellow>>logged in as {username}.")

    for index, (file_name, file_data) in enumerate(
        tqdm(items, desc="uploading files", total=total),
        start=1,
    ):
        file_path = file_data.get("file_path", None) if isinstance(file_data, dict) else None
        logger.debug(f"start uploading file: {file_name}.")
        summary = (
            f"Adding {file_data.get('new_languages')} languages translations from {main_title_link}"
            if isinstance(file_data, dict) and "new_languages" in file_data
            else f"Adding translations from {main_title_link}"
        )
        upload = upload_file(
            file_name,
            file_path,
            site=site,
            summary=summary,
        ) or {}

        result = upload.get("result") if isinstance(upload, dict) else None

        logger.debug(f"upload result: {result}")

        if result == "Success":
            done += 1
        elif result == "fileexists-no-change":
            no_changes += 1
        else:
            not_done += 1
            if isinstance(upload, dict) and "error" in upload:
                errors.append(upload.get("error"))

        stages["message"] = (
            f"Total Files: {total:,}, "
            f"uploaded {done:,}, "
            f"no changes: {no_changes:,}, "
            f"not uploaded: {not_done:,}"
        )
        if message_updater:
            message_updater(stages["message"])

    stages["status"] = "Failed" if not_done else "Completed"

    upload_result = {"done": done, "not_done": not_done, "no_changes": no_changes, "errors": errors}

    return upload_result, stages


def upload_task(
    stages: Dict[str, Any],
    files_to_upload: Dict[str, Dict[str, object]],
    main_title: str,
    do_upload: Optional[bool] = None,
    user: Dict[str, str] = None,
    store: TaskStorePyMysql =None,
    task_id: str = "",
):
    """
    Coordinate and run the file upload process, updating stage status and progress as files are processed.
    """

    def progress_updater(stage_state: Dict[str, Any]) -> None:
        """Forward upload progress updates to the task store."""
        store.update_stage(task_id, "upload", stage_state or stages)

    total = len(files_to_upload)
    stages["status"] = "Running"
    stages["message"] = f"Uploading files 0/{total:,}"

    progress_updater(stages)

    if not do_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (Upload disabled)"
        progress_updater(stages)
        return {"done": 0, "not_done": total, "skipped": True, "reason": "disabled"}, stages

    if not files_to_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (No files to upload)"
        progress_updater(stages)
        return {"done": 0, "not_done": 0, "skipped": True, "reason": "no-input"}, stages

    user = user or {}
    access_token = _coerce_encrypted(user.get("access_token"))
    access_secret = _coerce_encrypted(user.get("access_secret"))

    if not access_token or not access_secret:
        stages["status"] = "Failed"
        stages["message"] += " (Missing OAuth credentials)"
        # ---
        progress_updater(stages)
        # ---
        return {
            "done": 0,
            "not_done": total,
            "skipped": True,
            "reason": "missing-token",
        }, stages

    try:
        site = build_upload_site(access_token, access_secret)
    except Exception as exc:  # pragma: no cover - network interaction
        logger.exception("Failed to build OAuth site", exc_info=exc)
        stages["status"] = "Failed"
        stages["message"] += " (OAuth authentication failed)"
        progress_updater(stages)
        return {
            "done": 0,
            "not_done": total,
            "skipped": True,
            "reason": "oauth-auth-failed",
        }, stages

    user_id = user.get("id") if isinstance(user, dict) else None

    if isinstance(user_id, int):
        try:
            mark_token_used(user_id)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to record token usage", extra={"user_id": user_id})

    main_title_link = f"[[:File:{main_title}]]"

    def message_updater(value: str) -> None:
        store.update_stage_column(task_id, "upload", "stage_message", value)

    upload_result, stages = start_upload(
        files_to_upload,
        main_title_link,
        site,
        stages,
        message_updater,
    )

    return upload_result, stages
