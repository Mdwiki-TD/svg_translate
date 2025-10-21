"""Download task helper with progress callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import quote

import requests
from tqdm import tqdm

try:  # pragma: no cover - maintain compatibility with both package layouts
    from svg_translate.log import logger
except ImportError:  # pragma: no cover
    from src.svg_translate.log import logger  # type: ignore[no-redef]

PerFileCallback = Optional[Callable[[int, int, Path, str], None]]
ProgressUpdater = Optional[Callable[[Dict[str, Any]], None]]

USER_AGENT = "WikiMedBot/1.0 (https://meta.wikimedia.org/wiki/User:Mr.Ibrahem; mailto:example@example.org)"


def download_commons_svgs(
    titles: Iterable[str],
    output_dir: Path | str,
    *,
    per_file_callback: PerFileCallback = None,
) -> list[str]:
    """Backward-compatible wrapper returning the list of downloaded file paths."""

    files, _counts = _download_titles(list(titles), Path(output_dir), per_file_callback)
    return files


def _safe_invoke_callback(
    callback: PerFileCallback,
    index: int,
    total: int,
    target_path: Path,
    status: str,
) -> None:
    """Invoke a callback defensively, matching the upload helper signature."""

    if not callback:
        return
    try:
        callback(index, total, target_path, status)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Error while executing download progress callback")


def _download_titles(
    titles: Iterable[str],
    output_dir: Path,
    per_file_callback: PerFileCallback = None,
):
    titles = list(titles)
    out_dir = Path(str(output_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    files: list[str] = []
    counts = {"success": 0, "existing": 0, "failed": 0}

    for index, title in enumerate(tqdm(titles, total=len(titles), desc="Downloading files"), 1):
        result = download_one_file(title, out_dir, index, session)
        status = result["result"] or "failed"
        if status == "success":
            counts["success"] += 1
        elif status == "existing":
            counts["existing"] += 1
        else:
            counts["failed"] += 1

        target = Path(result["path"]) if result["path"] else out_dir / title
        if result["path"]:
            files.append(result["path"])

        if per_file_callback:
            _safe_invoke_callback(per_file_callback, index, len(titles), target, status)

    return files, counts


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
        logger.info(f"[{i}] Skipped existing: {title}")
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
    per_file_callback: PerFileCallback = None,
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

    def _notify(stage_state: Dict[str, Any]) -> None:
        if not progress_updater:
            return
        try:
            progress_updater(stage_state)
        except TypeError:
            try:
                progress_updater()
            except Exception:
                logger.exception("Download progress updater raised an error")
        except Exception:
            logger.exception("Download progress updater raised an error")

    _notify(stages)

    counts = {"success": 0, "existing": 0, "failed": 0}

    def tracking_callback(index: int, total_items: int, target_path: Path, status: str) -> None:
        resolved = status or "failed"
        if resolved == "success":
            counts["success"] += 1
        elif resolved == "existing":
            counts["existing"] += 1
        else:
            counts["failed"] += 1

        stages["message"] = f"Downloading {index:,}/{total:,}"
        _notify(stages)

        if per_file_callback:
            _safe_invoke_callback(per_file_callback, index, total_items, target_path, resolved)

    out_dir = Path(str(output_dir_main))
    files = download_commons_svgs(titles, out_dir, per_file_callback=tracking_callback)

    if counts["success"] == 0 and counts["existing"] == 0 and counts["failed"] == 0:
        counts["success"] = len(files)
        counts["failed"] = max(0, total - len(files))

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

    _notify(stages)

    return files, stages
