"""Svg viewer"""

from __future__ import annotations
import logging
from flask import (
    Blueprint,
    render_template,
    send_from_directory,
)
from .thumbnail_utils import save_thumb
from .utils import (
    svg_data_path,
    svg_data_thumb_path,
    get_files,
    get_informations,
    get_temp_title,
)

bp_explorer = Blueprint("explorer", __name__, url_prefix="/explorer")
logger = logging.getLogger(__name__)


@bp_explorer.get("/<title_dir>/downloads")
def by_title_downloaded(title_dir: str):
    files, title_path = get_files(title_dir, "files")

    title = get_temp_title(title_dir)

    return render_template(
        "explorer/explore_files1.html",
        head_title=f"{title} downloaded Files ({len(files):,})",
        path=str(title_path),
        title=title,
        title_dir=title_dir,
        subdir="files",
        files=files,
    )


@bp_explorer.get("/<title_dir>/translated")
def by_title_translated(title_dir: str):
    files, title_path = get_files(title_dir, "translated")

    title = get_temp_title(title_dir)

    return render_template(
        "explorer/explore_files1.html",
        head_title=f"({title}) Translated Files ({len(files):,})",
        path=str(title_path),
        title=title,
        title_dir=title_dir,
        subdir="translated",
        files=files,
    )


@bp_explorer.get("/<title_dir>/not_translated")
def by_title_not_translated(title_dir: str):
    downloaded, title_path = get_files(title_dir, "files")
    translated, _ = get_files(title_dir, "translated")

    title = get_temp_title(title_dir)

    not_translated = [x for x in downloaded if x not in translated]

    return render_template(
        "explorer/explore_files1.html",
        head_title=f"({title}) Not Translated Files ({len(not_translated):,})",
        path=str(title_path),
        title=title,
        title_dir=title_dir,
        subdir="files",
        files=not_translated,
    )


@bp_explorer.get("/<title>")
def by_title(title: str):
    infos = get_informations(title)

    return render_template(
        "explorer/folder.html",
        result=infos,
    )


@bp_explorer.get("/")
def main():
    titles = [x.name for x in svg_data_path.iterdir() if x.is_dir()]

    return render_template(
        "explorer/index.html",
        titles=titles
    )


@bp_explorer.route('/media/<title_dir>/<subdir>/<path:filename>')
def serve_media(title_dir="", subdir="", filename=""):
    """Serve SVG files"""
    dir_path = svg_data_path / title_dir / subdir
    dir_path = str(dir_path.absolute())

    # dir_path = "I:/SVG_EXPLORER/svg_data/Parkinsons prevalence/translated"
    return send_from_directory(dir_path, filename)


@bp_explorer.route('/media_thumb/<path:filename>')
def serve_thumb(title_dir="", subdir="", filename=""):
    # ---
    dir_path = svg_data_path / title_dir / subdir
    # ---
    thumb_path = svg_data_thumb_path / filename / title_dir / subdir
    # ---
    file_path = dir_path / filename
    file_thumb_path = thumb_path / filename
    # ---
    if not file_thumb_path.exists():
        save_thumb(file_path, file_thumb_path)
    # ---
    if file_thumb_path.exists():
        return send_from_directory(str(thumb_path.absolute()), filename)
    # ---
    return send_from_directory(str(dir_path.absolute()), filename)


__all__ = [
    "bp_explorer"
]
