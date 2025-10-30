
import json
import logging
from pathlib import Path
from ...config import settings

logger = logging.getLogger("svg_translate")


# svg_data_path = Path("I:/SVG/svg_data")
# svg_data_path = Path(__name__).parent.parent.parent / "svg_data"
svg_data_path = Path(settings.paths.svg_data)
svg_data_thumb_path = Path(settings.paths.svg_data_thumb)


def _validate_path_under_base(title: str, sub_dir: str) -> Path:
    """Resolve and validate that title/sub_dir is confined under BASE_SVG."""
    try:
        candidate = (svg_data_path / title / sub_dir).resolve()
    except (ValueError, OSError):
        raise PermissionError(f"Invalid path: title={title!r}, sub_dir={sub_dir!r}")

    if svg_data_path not in candidate.parents and candidate != svg_data_path:
        raise PermissionError(f"Path traversal attempt blocked: {candidate}")

    return candidate


def get_main_data(title, filename="files_stats.json"):
    file_path = svg_data_path / title / (filename or "files_stats.json")
    if not file_path.exists():
        return {}
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        logger.exception(f"Failed to read or parse {file_path}")
        return {}


def get_files_full_path(title, sub_dir):
    # title_path = svg_data_path / title / sub_dir

    try:
        title_path = _validate_path_under_base(title, sub_dir)
    except PermissionError as e:
        logger.warning(str(e))
        return [], svg_data_path / title / sub_dir

    if not title_path.exists():
        logger.error(f"Title path {title_path} does not exist")
        return [], title_path

    files = [str(x.name) for x in title_path.glob("*")]

    return files, title_path


def get_files(title, sub_dir):
    # title_path = svg_data_path / title / sub_dir
    try:
        title_path = _validate_path_under_base(title, sub_dir)
    except PermissionError as e:
        logger.warning(str(e))
        return [], svg_data_path / title / sub_dir

    if not title_path.exists():
        logger.error(f"Title path {title_path} does not exist")
        return [], title_path

    files = [
        x.name
        for x in title_path.glob("*.svg")
    ]

    return files, title_path


def get_languages(title: str, translations_data: dict|None=None) -> list:
    # ---
    languages = []
    # ---
    if not translations_data:
        translations_data = get_main_data(title, "translations.json") or {}
    # ---
    new = translations_data.get("new", {})
    # ---
    for key, v in new.items():
        if key == "default_tspans_by_id":
            continue
        if isinstance(v, dict):
            languages.extend(v.keys())
    # ---
    return sorted(set(languages))


def get_temp_title(title):
    temp_title = title
    temp_title_path = svg_data_path / title / "title.txt"

    text = temp_title_path.read_text(encoding="utf-8").strip() if temp_title_path.exists() else ""

    temp_title = text.strip() if text.strip() else title

    return temp_title or title


def get_informations(title):
    data = {}
    downloaded, title_path = get_files(title, "files")
    translated, _ = get_files(title, "translated")

    data = get_main_data(title)
    len_titles = len(data.get("titles", []))

    main_file = data.get("main_title", "")

    if main_file and not main_file.lower().startswith("file:"):
        main_file = f"File:{main_file}"

    languages = get_languages(title, data.get("translations"))

    # not_translated = set(downloaded).difference(translated)
    not_translated = [x for x in downloaded if x not in set(translated)]
    downloaded_set = {f.lower() for f in downloaded}
    not_downloaded = [
        (f"File:{x}" if not x.lower().startswith("file:") else x)
        for x in data.get("titles", [])
        if x.lower() not in downloaded_set
    ]
    temp_title = get_temp_title(title)

    result = {
        "title": temp_title,
        "title_dir": title,
        "main_file": main_file,
        "len_titles": len_titles,
        "languages": ", ".join(languages),
        "path": str(title_path.parent),
        "len_files" : {
            "not_downloaded": len(not_downloaded),
            "downloaded": len(downloaded),
            "translated": len(translated),
            "not_translated": len(not_translated)
        },
        "not_downloaded": not_downloaded,
    }
    return result
