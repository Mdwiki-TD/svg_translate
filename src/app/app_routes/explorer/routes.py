"""Svg viewer"""

from __future__ import annotations

import json
import logging
# from pathlib import Path

from flask import (
    Blueprint,
    render_template,
)

from flask import send_from_directory
from ...config import settings

bp_explorer = Blueprint("explorer", __name__, url_prefix="/explorer")
logger = logging.getLogger(__name__)


# svg_data_path = Path("I:/SVG/svg_data")
# svg_data_path = Path(__name__).parent.parent.parent / "svg_data"
svg_data_path = settings.paths.svg_data


def get_main_data(title, filename="files_stats.json"):
    file_path = svg_data_path / title / (filename or "files_stats.json")
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data
    except Exception:
        logger.error(f"File {file_path} does not exist")
        return {}


def get_files_full_path(title, sub_dir):
    title_path = svg_data_path / title / sub_dir
    if not title_path.exists():
        logger.error(f"Title path {title_path} does not exist")
        return [], title_path

    files = [str(x.name) for x in title_path.glob("*")]

    return files, title_path


def get_files(title, sub_dir):
    title_path = svg_data_path / title / sub_dir
    if not title_path.exists():
        logger.error(f"Title path {title_path} does not exist")
        return [], title_path

    files = [
        x.name
        for x in title_path.glob("*.svg")
    ]

    return files, title_path


@bp_explorer.get("/<title>/downloads")
def by_title_downloaded(title: str):
    files, title_path = get_files(title, "files")

    return render_template(
        "explorer/explore_files1.html",
        head_title=f"{title} downloaded Files ({len(files):,})",
        path=str(title_path),
        title=title,
        subdir="files",
        files=files,
    )


@bp_explorer.get("/<title>/translated")
def by_title_translated(title: str):
    files, title_path = get_files(title, "translated")

    return render_template(
        "explorer/explore_files1.html",
        head_title=f"({title}) Translated Files ({len(files):,})",
        path=str(title_path),
        title=title,
        subdir="translated",
        files=files,
    )


@bp_explorer.get("/<title>/not_translated")
def by_title_not_translated(title: str):
    downloaded, title_path = get_files(title, "files")
    translated, _ = get_files(title, "translated")

    not_translated = [x for x in downloaded if x not in translated]

    return render_template(
        "explorer/explore_files1.html",
        head_title=f"({title}) Not Translated Files ({len(not_translated):,})",
        path=str(title_path),
        title=title,
        subdir="files",
        files=not_translated,
    )


def get_languages(title: str, translations_data: dict|None=None) -> list:
    # ---
    languages = []
    # ---
    if not translations_data:
        translations_data = get_main_data(title, "translations.json") or {}
    # ---
    new = translations_data.get("new", {})
    # ---
    for x, v in new.items():
        if isinstance(v, dict):
            languages.extend(v.keys())
    # ---
    languages = list(set(languages))
    # ---
    languages.sort()
    # ---
    return languages


@bp_explorer.get("/<title>")
def by_title(title: str):
    downloaded, title_path = get_files(title, "files")
    translated, _ = get_files(title, "translated")

    data = get_main_data(title)
    len_titles = len(data.get("titles", []))

    main_title = data.get("main_title", "")

    if not main_title.lower().startswith("file:"):
        main_title = f"File:{main_title}"

    languages = get_languages(title, data.get("translations"))

    not_translated = [x for x in downloaded if x not in translated]

    not_downloaded = [
        (f"File:{x}" if not x.lower().startswith("file:") else x)
        for x in data.get("titles", [])
        if x not in downloaded
    ]

    result = {
        "title": title,
        "len_titles": len_titles,
        "languages": ", ".join(languages),
        "path": str(title_path.parent),
        "len_files" : {
            "not_downloaded": len(not_downloaded),
            "downloaded": len(downloaded),
            "translated": len(translated),
            "not_translated": len(not_translated)
        },
    }
    return render_template(
        "explorer/folder.html",
        result=result,
        main_title=main_title,
        downloaded=downloaded,
        translated=translated,
        not_downloaded=not_downloaded,
    )


@bp_explorer.get("/")
def main():
    titles = [x.name for x in svg_data_path.iterdir() if x.is_dir()]

    return render_template(
        "explorer/index.html",
        titles=titles
    )


@bp_explorer.route('/media/<title>/<subdir>/<path:filename>')
def serve_media(title="", subdir="", filename=""):
    """Serve SVG files"""
    dir_path = svg_data_path / title / subdir
    dir_path = str(dir_path.absolute())

    # dir_path = "I:/SVG_EXPLORER/svg_data/Parkinsons prevalence/translated"
    return send_from_directory(dir_path, filename)


__all__ = [
    "bp_explorer"
]
