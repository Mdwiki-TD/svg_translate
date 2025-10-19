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
    """Download SVG files from Wikimedia Commons with progress reporting."""
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
        url = base + quote(title)
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
    stages: Dict[str, Any],
    output_dir_main: Path,
    titles: Iterable[str],
    progress_updater: ProgressUpdater = None,
):
    titles = list(titles)
    total = len(titles)

    stages["message"] = f"Downloading 0/{total:,}"
    stages["status"] = "Running"

    if progress_updater:
        try:
            progress_updater(stages)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Error while executing progress updater")

    counts = {"success": 0, "skipped": 0, "failed": 0}

    def per_file_callback(index: int, total_items: int, _path: Path, status: str) -> None:
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
                progress_updater(stages)
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
            progress_updater(stages)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Error while executing progress updater")

    return files, stages
