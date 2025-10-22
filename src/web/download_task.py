"""Download task helper with progress callbacks."""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import quote

import requests
from tqdm import tqdm
from .db.task_store_pymysql import TaskStorePyMysql

USER_AGENT = os.getenv("USER_AGENT", "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)")

logger = logging.getLogger(__name__)


def download_one_file(title: str, out_dir: Path, i: int, session: requests.Session = None):
    """Download a single Commons file, skipping already-downloaded copies.

    Parameters:
        title (str): Title of the file page on Wikimedia Commons.
        out_dir (Path): Directory where the file should be stored.
        i (int): 1-based index used only for logging context.
        session (requests.Session | None): Optional shared session. A new session
            with an appropriate User-Agent is created when omitted.

    Returns:
        dict: Outcome dictionary with keys ``result`` ("success", "existing", or
        "failed") and ``path`` (path string when available).
    """
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
        logger.debug(f"[{i}] Skipped existing: {title}")
        data["result"] = "existing"
        data["path"] = str(out_path)
        return data
    if not session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
        })
    try:
        response = session.get(url, timeout=30, allow_redirects=True)
    except requests.RequestException as exc:
        data["result"] = "failed"
        logger.error(f"[{i}] Failed (network error): {title} -> {exc}")
        return data

    if response.status_code == 200:
        logger.debug(f"[{i}] Downloaded: {title}")
        out_path.write_bytes(response.content)
        logger.debug(f"[{i}] out_path: {str(out_path)}")
        data["result"] = "success"
        data["path"] = str(out_path)
    else:
        data["result"] = "failed"
        logger.error(f"[{i}] Failed (non-SVG or not found): {title}")

    return data


def download_task(
    task_id: str,
    stages: Dict[str, Any],
    output_dir_main: Path,
    titles: Iterable[str],
    store: TaskStorePyMysql =None,
):
    """
    Orchestrates downloading a set of Wikimedia Commons SVGs while updating a mutable stages dict and an optional progress updater.

    Parameters:
        stages (Dict[str, str]): Mutable mapping that will be updated with "message" and "status" to reflect current progress and final outcome.
        output_dir_main (Path): Directory where downloaded files will be saved.
        titles (Iterable[str]): Iterable of file titles to download.

    Returns:
        (files, stages) (Tuple[List[str], Dict[str, str]]): `files` is the list of downloaded file paths (as strings); `stages` is the same dict passed in, updated with a final "status" of "Completed" or "Failed" and a final "message" summarizing processed and failed counts.
    """
    titles = list(titles)
    total = len(titles)

    stages["message"] = f"Downloading 0/{total:,}"
    stages["status"] = "Running"

    store.update_stage(task_id, "download", stages)

    out_dir = Path(str(output_dir_main))
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    session.headers.update({
        "User-Agent": USER_AGENT,
    })

    def message_updater(value: str) -> None:
        store.update_stage_column(task_id, "download", "stage_message", value)

    files: list[str] = []

    done = 0
    not_done = 0
    existing = 0

    for index, title in enumerate(tqdm(titles, total=len(titles), desc="Downloading files"), 1):
        result = download_one_file(title, out_dir, index, session)
        status = result["result"] or "failed"
        if status == "success":
            done += 1
        elif status == "existing":
            existing += 1
        else:
            not_done += 1

        stages["message"] = f"Downloading {index:,}/{len(titles):,}"

        if result["path"]:
            files.append(result["path"])

        stages["message"] = (
            f"Total Files: {total:,}, "
            f"Downloaded {done:,}, "
            f"skip existing {existing:,}, "
            f"failed to download: {not_done:,}"
        )
        message_updater(stages["message"])

    logger.debug("files: %s", len(files))

    stages["status"] = "Failed" if not_done else "Completed"

    logger.debug(
        "Downloaded %s files, skipped %s existing files, failed to download %s files",
        done,
        existing,
        not_done,
    )

    return files, stages
