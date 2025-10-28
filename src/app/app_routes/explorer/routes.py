"""Svg viewer"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import (
    Blueprint,
    render_template,
    jsonify,
)

from ...config import settings

bp_explorer = Blueprint("explorer", __name__, url_prefix="/explorer")
logger = logging.getLogger(__name__)


def get_main_title(title):
    file_path = Path(settings.paths.svg_data) / title / "files_stats.json"
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data.get("main_title", "")
    except Exception:
        logger.error(f"File {file_path} does not exist")
        return None


def get_files(title, sub_dir):
    svg_data_path = settings.paths.svg_data
    title_path = Path(svg_data_path) / title / sub_dir
    if not title_path.exists():
        logger.error(f"Title path {title_path} does not exist")
        return [], title_path

    files = [str(x) for x in title_path.glob("*")]

    return files, title_path


@bp_explorer.get("/<title>/downloads")
def by_title_downloaded(title: str):
    files, title_path = get_files(title, "files")

    return jsonify({"title": title, "path": str(title_path), "files": files})


@bp_explorer.get("/<title>/translated")
def by_title_translated(title: str):
    files, title_path = get_files(title, "translated")

    return jsonify({"title": title, "path": str(title_path), "files": files})


@bp_explorer.get("/<title>")
def by_title(title: str):
    downloaded, title_path = get_files(title, "files")
    translated, _ = get_files(title, "translated")
    main_title = get_main_title(title)
    result = {
        "title": title,
        "main_title": main_title,
        "path": str(title_path.parent),
        "files" : {
            "downloaded": len(downloaded),
            "translated": len(translated)
        }
    }
    return render_template(
        "explorer/folder.html",
        result=result,
        main_title=main_title,
        downloaded=downloaded,
        translated=translated,
    )


@bp_explorer.get("/")
def main():
    svg_data_path = Path(settings.paths.svg_data)
    titles = [x.name for x in svg_data_path.iterdir() if x.is_dir()]

    return render_template(
        "explorer/index.html",
        titles=titles
    )


__all__ = [
    "bp_explorer"
]
