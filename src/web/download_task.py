"""Download task helper with progress callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import quote

import requests
from tqdm import tqdm

from svg_translate import logger

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


def download_one_file(title: str, session: requests.Session, out_dir: Path | str, i: int):
    base = "https://ar.wikipedia.org/wiki/Special:FilePath/"

    data = {
        "result" : "",
        "path": "",
    }

    if not title:
        return data

    url = f"{base}{quote(title)}"
    out_path = out_dir / title

    if out_path.exists():
        logger.info(f"[{i}] Skipped existing: {title}")
        data["result"] = "existing"
        data["path"] = str(out_path)
        return data

    try:
        response = session.get(url, timeout=30, allow_redirects=True)
    except requests.RequestException as exc:
        data["result"] = "failed"
        logger.error(f"[{i}] Failed (network error): {title} -> {exc}")
        return data

    if response.status_code == 200:
        logger.info(f"[{i}] Downloaded: {title}")
        out_path.write_bytes(response.content)
        data["result"] = "success"
        data["path"] = str(out_path)
    else:
        data["result"] = "failed"
        logger.error(f"[{i}] Failed (non-SVG or not found): {title}")

    return data


def download_task(
    stages: Dict[str, Any],
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

    if progress_updater:
        progress_updater(stages)

    counts = {"success": 0, "existing": 0, "failed": 0}

    out_dir = Path(str(output_dir_main))
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    session.headers.update({
        "User-Agent": "WikiMedBot/1.0 (https://meta.wikimedia.org/wiki/User:Mr.Ibrahem; mailto:example@example.org)",
    })

    files = []

    for i, title in tqdm(enumerate(titles, 1), total=len(titles), desc="Downloading files"):
        result = download_one_file(title, session, out_dir=out_dir)
        if result["result"] == "success":
            counts["success"] += 1
        elif result["result"] == "existing":
            counts["existing"] += 1
        else:
            counts["failed"] += 1

        stages["message"] = f"Downloading {i:,}/{len(titles):,}"

        if result["path"]:
            files.append(result["path"])

        if progress_updater:
            progress_updater(stages)

    logger.info("files: %s", len(files))

    logger.info(
        "Downloaded %s files, skipped %s existing files, failed to download %s files",
        counts["success"],
        counts["existing"],
        counts["failed"],
    )

    processed = counts["success"] + counts["existing"]
    if counts["failed"]:
        stages["status"] = "Failed"
        stages["message"] = (
            f"Downloaded {processed:,}/{total:,} (Failed: {counts['failed']:,})"
        )
    else:
        stages["status"] = "Completed"
        stages["message"] = f"Downloaded {processed:,}/{total:,}"

    if progress_updater:
        progress_updater(stages)

    return files, stages
