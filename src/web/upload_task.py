"""Upload task helpers with progress callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional

import mwclient
from tqdm import tqdm

from svg_translate import logger
from svg_translate.commons.upload_bot import upload_file
from user_info import username, password

PerFileCallback = Optional[Callable[[int, int, Path, str], None]]
ProgressUpdater = Optional[Callable[[], None]]


def _safe_invoke_callback(
    callback: PerFileCallback,
    index: int,
    total: int,
    target_path: Path,
    status: str,
) -> None:
    if not callback:
        return
    try:
        callback(index, total, target_path, status)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Error while executing progress callback")


def start_upload(
    files_to_upload: Dict[str, Dict[str, object]],
    main_title_link: str,
    username_value: str,
    password_value: str,
    per_file_callback: PerFileCallback = None,
):
    site = mwclient.Site("commons.m.wikimedia.org")

    try:
        site.login(username_value, password_value)
    except mwclient.errors.LoginError as exc:  # pragma: no cover - network interaction
        print(f"Could not login error: {exc}")

    if site.logged_in:
        print(f"<<yellow>>logged in as {site.username}.")

    done = 0
    not_done = 0
    errors = []

    items = list(files_to_upload.items())
    total = len(items)

    for index, (file_name, file_data) in enumerate(
        tqdm(items, desc="uploading files", total=total),
        start=1,
    ):
        file_path = file_data.get("file_path", None) if isinstance(file_data, dict) else None
        print(f"start uploading file: {file_name}.")
        summary = (
            f"Adding {file_data['new_languages']} languages translations from {main_title_link}"
            if isinstance(file_data, dict) and "new_languages" in file_data
            else f"Adding translations from {main_title_link}"
        )
        upload = upload_file(
            file_name,
            file_path,
            site=site,
            username=username_value,
            password=password_value,
            summary=summary,
        ) or {}
        result = upload.get("result") if isinstance(upload, dict) else None
        print(f"upload: {result}")

        status = "success" if result == "Success" else "failed"
        if result == "Success":
            done += 1
        else:
            not_done += 1
            if isinstance(upload, dict) and "error" in upload:
                errors.append(upload.get("error"))

        target_path = Path(file_path) if file_path else Path(file_name)
        _safe_invoke_callback(per_file_callback, index, total, target_path, status)

    return {"done": done, "not_done": not_done, "errors": errors}


def upload_task(
    stages: Dict[str, str],
    files_to_upload: Dict[str, Dict[str, object]],
    main_title: str,
    do_upload: Optional[bool] = None,
    progress_updater: ProgressUpdater = None,
):
    total = len(files_to_upload)
    stages["status"] = "Running"
    stages["message"] = f"Uploading files 0/{total:,}"

    if not do_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (Upload disabled)"
        return {"done": 0, "not_done": total, "skipped": True, "reason": "disabled"}, stages

    if not files_to_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (No files to upload)"
        return {"done": 0, "not_done": 0, "skipped": True, "reason": "no-input"}, stages

    if not username or not password:
        stages["status"] = "Failed"
        stages["message"] += " (Missing credentials)"
        return {
            "done": 0,
            "not_done": total,
            "skipped": True,
            "reason": "missing-creds",
        }, stages

    main_title_link = f"[[:File:{main_title}]]"

    counts = {"success": 0, "failed": 0}

    def per_file_callback(index: int, total_items: int, _path: Path, status: str) -> None:
        if status == "success":
            counts["success"] += 1
            prefix = "Uploaded"
        else:
            counts["failed"] += 1
            prefix = "Failed"

        stages["message"] = f"{prefix} {index:,}/{total_items:,}"

        if progress_updater:
            try:
                progress_updater()
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Error while executing progress updater")

    upload_result = start_upload(
        files_to_upload,
        main_title_link,
        username,
        password,
        per_file_callback=per_file_callback,
    )

    stages["message"] = (
        f"Total Files: {total:,}, "
        f"Files uploaded {upload_result['done']:,}, "
        f"Files not uploaded: {upload_result['not_done']:,}"
    )

    if upload_result["not_done"]:
        stages["status"] = "Failed"
    else:
        stages["status"] = "Completed"

    if progress_updater:
        try:
            progress_updater()
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Error while executing progress updater")

    return upload_result, stages
