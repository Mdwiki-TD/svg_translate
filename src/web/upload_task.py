"""Upload task helpers with progress callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

import mwclient
from tqdm import tqdm

try:
    from mwclient.auth import OAuthAuthentication
except (ImportError, AttributeError):  # pragma: no cover - optional dependency in tests
    OAuthAuthentication = None  # type: ignore[assignment]

try:  # pragma: no cover - maintain compatibility with both package layouts
    from svg_translate.log import logger
    from svg_translate.commons.upload_bot import upload_file
except ImportError:  # pragma: no cover - fallback when running from src package
    from src.svg_translate.log import logger  # type: ignore[no-redef]
    from src.svg_translate.commons.upload_bot import upload_file  # type: ignore[no-redef]

PerFileCallback = Optional[Callable[[int, int, Path, str], None]]
ProgressUpdater = Optional[Callable[[Dict[str, Any]], None]]


def _safe_invoke_callback(
    callback: PerFileCallback,
    index: int,
    total: int,
    target_path: Path,
    status: str,
) -> None:
    """
    Invoke a per-file progress callback if one is provided, catching and logging any exceptions.

    Parameters:
        callback (Optional[Callable[[int, int, Path, str], None]]): The per-file callback to invoke; may be None.
        index (int): 1-based index of the file within the total upload batch.
        total (int): Total number of files being uploaded.
        target_path (Path): Path to the file that was (attempted to be) uploaded.
        status (str): Upload status for the file (e.g., "success" or "failed").
    """
    if not callback:
        return
    try:
        callback(index, total, target_path, status)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Error while executing progress callback")


def start_upload(
    files_to_upload: Dict[str, Dict[str, object]],
    main_title_link: str,
    oauth_credentials: Dict[str, str],
    per_file_callback: PerFileCallback = None,
):
    """
    Upload multiple files to Wikimedia Commons and invoke a per-file progress callback.

    Parameters:
        files_to_upload (Dict[str, Dict[str, object]]): Mapping from target file name to metadata. Each value may include:
            - "file_path" (str): local path to the file to upload.
            - "new_languages" (Any): optional value used to build the upload summary.
        main_title_link (str): Wiki-file link (e.g., "[[:File:Title]]") used in the upload summary.
        oauth_credentials (Dict[str, str]): OAuth credential bundle containing consumer and access tokens.
        per_file_callback (Optional[Callable[[int, int, Path, str], None]]): Optional callback invoked after each file with
            parameters (index, total, target_path, status) where status is "success" or "failed".

    Returns:
        dict: Summary of the upload run with keys:
            - "done" (int): number of successfully uploaded files.
            - "not_done" (int): number of files that failed to upload.
            - "errors" (List[Any]): collected error messages from failed uploads.
    """
    if OAuthAuthentication is None:
        raise RuntimeError("mwclient OAuth support is unavailable")

    auth = OAuthAuthentication(
        oauth_credentials.get("consumer_key"),
        oauth_credentials.get("consumer_secret"),
        oauth_credentials.get("access_token"),
        oauth_credentials.get("access_secret"),
    )
    site = mwclient.Site(
        ("https", "commons.wikimedia.org"),
        clients_useragent="svgtranslate/1.0",
        path="/w/",
        auth=auth,
    )

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
    stages: Dict[str, Any],
    files_to_upload: Dict[str, Dict[str, object]],
    main_title: str,
    do_upload: Optional[bool] = None,
    oauth_credentials: Dict[str, str] | None = None,
    progress_updater: ProgressUpdater = None,
):
    """
    Coordinate and run the file upload process, updating stage status and progress as files are processed.

    Parameters:
        stages (Dict[str, str]): Mutable stage state; this function updates "status" and "message" to reflect progress and final outcome.
        files_to_upload (Dict[str, Dict[str, object]]): Mapping of filenames to their upload metadata; determines the total files to process.
        main_title (str): Title used to construct the main file link included in upload summaries.
        do_upload (Optional[bool]): Feature flag that enables or disables performing uploads; falsy values cause the task to skip uploading.
        progress_updater (Optional[Callable[[], None]]): Optional callback invoked after each per-file progress update and once at completion; exceptions from this callback are caught and logged.

    Returns:
        upload_result (Dict[str, object]), stages (Dict[str, str]):
                - upload_result: Summary of upload outcomes with keys:
                        - "done" (int): number of successfully uploaded files.
                        - "not_done" (int): number of files that were not uploaded.
                        - "errors" (List[str], optional): collected error messages from failed uploads.
                        - "skipped" (bool, optional): true when the upload was skipped and "reason" provides why.
                - stages: The final stage state dictionary (same object passed in) with updated "status" and "message".
    """
    total = len(files_to_upload)
    stages["status"] = "Running"
    stages["message"] = f"Uploading files 0/{total:,}"

    if progress_updater:
        progress_updater(stages)

    if not do_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (Upload disabled)"
        if progress_updater:
            progress_updater(stages)
        return {"done": 0, "not_done": total, "skipped": True, "reason": "disabled"}, stages

    if not files_to_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (No files to upload)"
        if progress_updater:
            progress_updater(stages)
        return {"done": 0, "not_done": 0, "skipped": True, "reason": "no-input"}, stages

    credentials = oauth_credentials or {}
    required_fields = ("consumer_key", "consumer_secret", "access_token", "access_secret")
    if not all(credentials.get(field) for field in required_fields):
        stages["status"] = "Failed"
        stages["message"] += " (Missing OAuth credentials)"
        if progress_updater:
            progress_updater(stages)
        return {
            "done": 0,
            "not_done": total,
            "skipped": True,
            "reason": "missing-oauth",
        }, stages

    main_title_link = f"[[:File:{main_title}]]"

    counts = {"success": 0, "failed": 0}

    def per_file_callback(index: int, total_items: int, _path: Path, status: str) -> None:
        """
        Update upload counters and the stage message for a single file, then invoke the progress updater if provided.

        Parameters:
            index (int): 1-based index of the current file in the upload sequence.
            total_items (int): Total number of files being uploaded.
            _path (Path): Path of the file; accepted for callback signature compatibility and not used.
            status (str): Upload outcome for the file; expected values include "success" or other strings indicating failure.

        Notes:
            - Increments the appropriate counter for success or failure and sets the stage message to reflect the current progress (for example, "Uploaded 3/10" or "Failed 2/10").
            - If a progress_updater is provided, it will be called; exceptions from the updater are caught and logged.
        """
        if status == "success":
            counts["success"] += 1
            prefix = "Uploaded"
        else:
            counts["failed"] += 1
            prefix = "Failed"

        stages["message"] = f"{prefix} {index:,}/{total_items:,}"

        if progress_updater:
            progress_updater(stages)

    upload_result = start_upload(
        files_to_upload,
        main_title_link,
        credentials,
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
        progress_updater(stages)

    return upload_result, stages
