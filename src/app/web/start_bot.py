import json
import html
from urllib.parse import quote
import logging
from CopySvgTranslate import extract  # type: ignore

from .commons import get_files, get_wikitext
from ..download_tasks import download_one_file

logger = logging.getLogger(__name__)


def json_save(path, data):
    """
    Save Python data to a file as pretty-printed UTF-8 JSON.

    If `data` is None or empty, the function logs an error and returns without writing. Errors encountered while opening or writing the file are logged and not propagated.

    Parameters:
        path (str | os.PathLike): Destination file path where JSON will be written.
        data: JSON-serializable Python object to persist (e.g., dict, list).
    """
    logger.debug(f"Saving json to: {path}")

    if not data or data is None:
        logger.error(f"Empty data to save to: {path}")
        return
    # ---
    try:
        # p = Path(path)
        # p.parent.mkdir(parents=True, exist_ok=True)
        # with p.open("w", encoding="utf-8") as f:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    except (OSError, TypeError, ValueError, Exception) as e:
        logger.error(f"Error saving json: {e}, path: {str(path)}")


def commons_link(title, name=None):
    """Return an HTML anchor pointing to a Commons file page.

    Parameters:
        title (str): Page title used to build the Commons URL.
        name (str | None): Optional link text; falls back to ``title`` when None.

    Returns:
        str: HTML anchor tag safe for embedding in status messages.
    """
    safe_name = html.escape(name or title, quote=True)
    href = f"https://commons.wikimedia.org/wiki/{quote(title, safe='/:()')}"
    return f"<a href='{href}' target='_blank' rel='noopener noreferrer'>{safe_name}</a>"


def save_files_stats(data, output_dir):
    """Persist workflow statistics to ``files_stats.json`` within output_dir.

    Parameters:
        data (dict): Serializable summary data to write.
        output_dir (pathlib.Path): Directory that will receive the JSON file.
    """

    files_stats_path = output_dir / "files_stats.json"
    json_save(files_stats_path, data)

    logger.debug(f"files_stats at: {files_stats_path}")


def make_results_summary(len_files, files_to_upload_count, no_file_path, injects_result, translations, main_title, upload_result):
    """Compile the final task result payload consumed by the UI and API.

    Parameters:
        len_files (int): Total number of files processed during the workflow.
        files_to_upload_count (int): Number of files with paths suitable for
            upload.
        no_file_path (int): Count of files lacking translated output paths.
        injects_result (dict): Aggregated statistics from the injection phase.
        translations (dict): Translation data summary used for injection.
        main_title (str): The primary Commons title associated with the task.
        upload_result (dict): Outcome of the upload stage.

    Returns:
        dict: Summary dictionary persisted to the database for task results.
    """
    return {
        "total_files": len_files,
        "files_to_upload_count": files_to_upload_count,
        "no_file_path": no_file_path,
        "injects_result": {
            "nested_files": injects_result.get('nested_files', 0),
            "saved_done": injects_result.get('saved_done', 0),
            "no_save": injects_result.get('no_save', 0),
        },
        "new_translations_count": len(translations.get("new", {})),
        "upload_result": upload_result,
        "main_title": main_title,
    }


def text_task(stages, title):
    """Fetch wikitext for a Commons file and update stage metadata.

    Parameters:
        stages (dict): Mutable stage metadata for the text stage.
        title (str): Commons title whose wikitext should be retrieved.

    Returns:
        tuple: ``(text, stages)`` where ``text`` is the retrieved wikitext (empty
        string on failure) and ``stages`` reflects the final status update.
    """

    stages["status"] = "Running"

    stages["sub_name"] = title  # commons_link(title)
    stages["message"] = "Load wikitext"
    # ---
    text = get_wikitext(title)

    if not text:
        stages["status"] = "Failed"
        logger.error("NO TEXT")
    else:
        stages["status"] = "Completed"
    return text, stages


def titles_task(stages, text, manual_main_title, titles_limit=None):
    """Extract SVG titles from wikitext and update stage metadata.

    Parameters:
        stages (dict): Mutable stage metadata for the titles stage.
        text (str): Wikitext retrieved from the main Commons page.
        manual_main_title (str | None): Optional title to use instead of the extracted main_title.
        titles_limit (int | None): Optional maximum number of titles to keep.

    Returns:
        tuple: ``({"main_title": str | None, "titles": list[str]}, stages)`` with
        the updated stage metadata.
    """

    stages["status"] = "Running"

    main_title, titles = get_files(text)

    if manual_main_title:
        main_title = manual_main_title

    if not titles or not main_title:
        stages["status"] = "Failed"
        logger.error("no titles")
    else:
        stages["status"] = "Completed"

    stages["message"] = f"Found {len(titles):,} titles"

    if titles_limit and titles_limit > 0 and len(titles) > titles_limit:
        stages["message"] += f", use only {titles_limit:,}"
        # use only n titles
        titles = titles[:titles_limit]

    if not main_title:
        stages["message"] += ", no main title found"

    data = {
        "main_title": main_title,
        "titles": titles
    }

    return data, stages


def translations_task(stages, main_title, output_dir_main):
    # ---
    """
    Load SVG translations from a Wikimedia Commons main file, save them as translations.json next to the provided output path, and update the given stages status mapping.

    Parameters:
        stages (dict): Mutable mapping updated with progress keys such as "sub_name", "message", and "status".
        main_title (str): Commons file title (e.g., "Example.svg") to download and extract translations from.
        output_dir_main (pathlib.Path): Directory where the downloaded main file is placed; the function writes translations.json to output_dir_main.parent.

    Returns:
        tuple: (translations, stages) where `translations` is a dict of extracted translations (empty if none were found or download failed) and `stages` is the same stages mapping updated to reflect the final status and messages.
    """
    stages["sub_name"] = f'File:{main_title}'  # commons_link(f'File:{main_title}')
    # ---
    stages["message"] = "Load translations from main file"
    # ---
    stages["status"] = "Running"
    # ---
    files1 = download_one_file(main_title, output_dir_main, 0)
    if not files1.get("path"):
        logger.error(f"when downloading main file: {main_title}")
        stages["message"] = "Error when downloading main file"
        stages["status"] = "Failed"
        return {}, stages

    main_title_path = files1["path"]
    translations = extract(main_title_path, case_insensitive=True)

    if not translations:
        logger.debug(f"No translations found in main file: {main_title}")
        stages["message"] = "No translations found in main file"
        stages["status"] = "Failed"
        # ---
        return {}, stages
    # ---
    new_translations = (translations.get("new") or {}) if isinstance(translations, dict) else {}

    new_translations_count = len(new_translations)

    if new_translations_count == 0:
        logger.debug(f"No translations found in main file: {main_title}")
        stages["status"] = "Failed"
        stages["message"] = "No translations found in main file"
        return {}, stages
    # ---
    stages["status"] = "Completed"
    # ---
    json_save(output_dir_main.parent / "translations.json", translations)
    # ---
    stages["message"] = f"Loaded {new_translations_count:,} translations from main file"
    # ---
    return translations, stages
