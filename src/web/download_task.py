"""Download task helper with progress callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Iterable, Optional
from urllib.parse import quote

import requests
from tqdm import tqdm

from svg_translate import logger

PerFileCallback = Optional[Callable[[int, int, Path, str], None]]
ProgressUpdater = Optional[Callable[[], None]]


def _safe_invoke_callback(
    callback: PerFileCallback,
    index: int,
    total: int,
    target_path: Path,
    status: str,
) -> None:
    """
    Safely invoke a per-file progress callback without allowing exceptions to propagate.

    If `callback` is None this function returns immediately. When a callback is provided,
    it is called with (index, total, target_path, status); any exception raised by the
    callback is caught and logged so it does not affect the caller.

    Parameters:
        callback (PerFileCallback): Optional callable to report per-file progress.
        index (int): 1-based index of the current file being processed.
        total (int): Total number of files being processed.
        target_path (Path): Destination path for the current file.
        status (str): Status label for the current file (e.g., "success", "skipped", "failed").
    """
    if not callback:
        return
    try:
        callback(index, total, target_path, status)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Error while executing progress callback")


def download_commons_svgs(
    titles: Iterable[str],
    out_dir: Path | str,
    per_file_callback: PerFileCallback = None,
):
    """
    Download the given Wikimedia Commons SVG titles into the specified output directory and report per-file progress via an optional callback.

    Parameters:
        titles (Iterable[str]): Iterable of file titles to download (e.g., "File:Example.svg").
        out_dir (Path | str): Destination directory where files will be saved; it will be created if it does not exist.
        per_file_callback (Optional[Callable[[int, int, Path, str], None]]): Optional callable invoked after each file attempt with
            (index, total, target_path, status) where status is one of "success", "skipped", or "failed".

    Returns:
        files (List[str]): List of file paths (as strings) that were written or already existed in out_dir.
    """
    out_dir = Path(str(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    base = "https://ar.wikipedia.org/wiki/Special:FilePath/"

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "WikiMedBot/1.0 (https://meta.wikimedia.org/wiki/User:Mr.Ibrahem; mailto:example@example.org)",
        }
    )

    titles = list(titles)
    files: list[str] = []

    existing = 0
    failed = 0
    success = 0

    for i, title in tqdm(enumerate(titles, 1), total=len(titles), desc="Downloading files"):
        if not title:
            continue
        url = f"{base}{quote(title)}"
        # url = f"{base}{title}"
        out_path = out_dir / title

        if out_path.exists():
            logger.info(f"[{i}] Skipped existing: {title}")
            existing += 1
            files.append(str(out_path))
            _safe_invoke_callback(per_file_callback, i, len(titles), out_path, "skipped")
            continue

        try:
            response = session.get(url, timeout=30, allow_redirects=True)
        except requests.RequestException as exc:
            failed += 1
            logger.error(f"[{i}] Failed (network error): {title} -> {exc}")
            _safe_invoke_callback(per_file_callback, i, len(titles), out_path, "failed")
            continue

        if response.status_code == 200:
            logger.info(f"[{i}] Downloaded: {title}")
            out_path.write_bytes(response.content)
            success += 1
            files.append(str(out_path))
            _safe_invoke_callback(per_file_callback, i, len(titles), out_path, "success")
        else:
            failed += 1
            logger.error(f"[{i}] Failed (non-SVG or not found): {title}")
            _safe_invoke_callback(per_file_callback, i, len(titles), out_path, "failed")

    logger.info(
        "Downloaded %s files, skipped %s existing files, failed to download %s files",
        success,
        existing,
        failed,
    )

    return files


def download_task(
    stages: Dict[str, str],
    output_dir_main: Path,
    titles: Iterable[str],
    progress_updater: ProgressUpdater = None,
):
    """
    Orchestrates downloading a set of Wikimedia Commons SVGs while updating a mutable stages dict and an optional progress updater.

    Parameters:
        stages (Dict[str, str]): Mutable mapping that will be updated with "message" and "status" to reflect current progress and final outcome.
        output_dir_main (Path): Directory where downloaded files will be saved.
        titles (Iterable[str]): Iterable of file titles to download.
        progress_updater (Optional[Callable[[], None]]): Optional callable invoked after each file update and once at the end to notify external progress observers.

    Returns:
        (files, stages) (Tuple[List[str], Dict[str, str]]): `files` is the list of downloaded file paths (as strings); `stages` is the same dict passed in, updated with a final "status" of "Completed" or "Failed" and a final "message" summarizing processed and failed counts.
    """
    titles = list(titles)
    total = len(titles)

    stages["message"] = f"Downloading 0/{total:,}"
    stages["status"] = "Running"

    counts = {"success": 0, "skipped": 0, "failed": 0}

    def per_file_callback(index: int, total_items: int, _path: Path, status: str) -> None:
        """
        Update aggregate download counts and the stages message for a single file, then invoke the optional progress updater.

        Parameters:
            index (int): 1-based position of the current file in the total sequence.
            total_items (int): Total number of files being processed.
            _path (Path): Path of the current file (not used by this callback).
            status (str): Outcome for the file; expected values: "success", "skipped", or other values treated as failure.

        Description:
            Increments the appropriate counter in the enclosing `counts` dictionary based on `status`,
            updates `stages["message"]` to a human-readable progress string like "Downloaded 3/10",
            and calls `progress_updater()` if one is provided; exceptions from the updater are caught and logged.
        """
        if status == "success":
            counts["success"] += 1
            prefix = "Downloaded"
        elif status == "skipped":
            counts["skipped"] += 1
            prefix = "Skipped"
        else:
            counts["failed"] += 1
            prefix = "Failed"

        stages["message"] = f"{prefix} {index:,}/{total_items:,}"

        if progress_updater:
            try:
                progress_updater()
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Error while executing progress updater")

    files = download_commons_svgs(
        titles,
        out_dir=output_dir_main,
        per_file_callback=per_file_callback,
    )

    logger.info("files: %s", len(files))

    processed = counts["success"] + counts["skipped"]
    if counts["failed"]:
        stages["status"] = "Failed"
        stages["message"] = (
            f"Downloaded {processed:,}/{total:,} (Failed: {counts['failed']:,})"
        )
    else:
        stages["status"] = "Completed"
        stages["message"] = f"Downloaded {processed:,}/{total:,}"

    if progress_updater:
        try:
            progress_updater()
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Error while executing progress updater")

    return files, stages
