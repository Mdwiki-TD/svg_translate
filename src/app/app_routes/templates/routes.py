"""Svg viewer"""

from pathlib import Path
import logging
import re
import json

from flask import (
    Blueprint,
    render_template,
)
from ...web.commons.category import get_category_members
from ...config import settings

bp_templates = Blueprint("templates", __name__, url_prefix="/templates")
logger = logging.getLogger(__name__)


def get_main_data(title):
    file_path = Path(settings.paths.svg_data) / title / "files_stats.json"
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        logger.exception(f"Failed to read or parse {file_path}")
        return {}


def temp_data(temp: str) -> dict:
    result = {
        "title_dir": "",
        "main_file": "",
    }
    # ---
    title_dir = Path(temp).name
    title_dir = re.sub(r'[^A-Za-z0-9._\- ]+', "_", str(title_dir)).strip("._")
    title_dir = title_dir.replace(" ", "_").lower()
    # ---
    out = Path(settings.paths.svg_data) / title_dir
    # ---
    if out.exists():
        result["title_dir"] = title_dir
        main_data = get_main_data(title_dir) or {}
        main_file = main_data.get("main_title")
        if main_file:
            value = f"File:{main_file}" if not main_file.lower().startswith("file:") else main_file
            result["main_file"] = value
    # ---
    return result


@bp_templates.get("/")
def main():
    templates = get_category_members("Category:Pages using gadget owidslider")
    templates = [
        x for x in templates
        if x.startswith("Template:")
        and x.lower() not in ["template:owidslider", "template:owid"]
    ]
    data = {
        temp : temp_data(temp)
        for temp in templates
    }
    # sort data by if they have main_file
    data = dict(sorted(data.items(), key=lambda x: x[1].get("main_file", ""), reverse=True))
    return render_template(
        "templates/index.html",
        data=data
    )


__all__ = [
    "bp_templates"
]
