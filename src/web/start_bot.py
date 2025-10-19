
import json
import html
from urllib.parse import quote

from svg_translate import download_commons_svgs, get_files, get_wikitext, start_injects, extract, logger


def json_save(path, data):
    """
    Save Python data to a file as pretty-printed UTF-8 JSON.

    If `data` is None or empty, the function logs an error and returns without writing. Errors encountered while opening or writing the file are logged and not propagated.

    Parameters:
        path (str | os.PathLike): Destination file path where JSON will be written.
        data: JSON-serializable Python object to persist (e.g., dict, list).
    """
    logger.info(f"Saving json to: {path}")

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
    safe_name = html.escape(name or title, quote=True)
    href = f"https://commons.wikimedia.org/wiki/{quote(title, safe='/:()')}"
    return f"<a href='{href}' target='_blank' rel='noopener noreferrer'>{safe_name}</a>"


def save_files_stats(data, output_dir):

    files_stats_path = output_dir / "files_stats.json"
    json_save(files_stats_path, data)

    logger.info(f"files_stats at: {files_stats_path}")


def make_results_summary(len_files, files_to_upload_count, no_file_path, injects_result, translations, main_title, upload_result):
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

    stages["status"] = "Running"

    stages["sub_name"] = commons_link(title)
    stages["message"] = "Load wikitext"
    # ---
    text = get_wikitext(title)

    if not text:
        stages["status"] = "Failed"
        logger.error("NO TEXT")
    else:
        stages["status"] = "Completed"
    return text, stages


def titles_task(stages, text, titles_limit=None):

    stages["status"] = "Running"

    main_title, titles = get_files(text)

    if not titles:
        stages["status"] = "Failed"
        logger.error("no titles")
    else:
        stages["status"] = "Completed"

    stages["message"] = f"Found {len(titles):,} titles"

    if titles_limit and titles_limit > 0 and len(titles) > titles_limit:
        stages["message"] += f", use only {titles_limit:,}"
        # use only n titles
        titles = titles[:titles_limit]

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
    stages["sub_name"] = commons_link(f'File:{main_title}')
    # ---
    stages["message"] = "Load translations from main file"
    # ---
    stages["status"] = "Running"
    # ---
    files1 = download_commons_svgs([main_title], out_dir=output_dir_main)
    if not files1:
        logger.error(f"when downloading main file: {main_title}")
        stages["message"] = "Error when downloading main file"
        stages["status"] = "Failed"
        return {}, stages

    main_title_path = files1[0]
    translations = extract(main_title_path, case_insensitive=True)

    stages["status"] = "Failed" if not translations else "Completed"

    if not translations:
        logger.info(f"Couldn't load translations from main file: {main_title}")
        stages["message"] = "Couldn't load translations from main file"
        # ---
        return translations, stages
    # ---
    json_save(output_dir_main.parent / "translations.json", translations)
    # ---
    stages["message"] = f"Loaded {len(translations.get('new', {})):,} translations from main file"
    # ---
    return translations, stages


def inject_task(stages, files, translations, output_dir=None, overwrite=False):
    # ---
    """
    Perform translation injection on a list of files and write translated outputs under output_dir/translated.

    Parameters:
        stages (dict): Mutable status object updated in-place with keys like "status", "message", and "sub_name".
        files (Sequence[pathlib.Path] or list): Iterable of file paths to process.
        translations (dict): Mapping of translation data used for injections.
        output_dir (pathlib.Path): Directory where a "translated" subdirectory will be created to store outputs.
        overwrite (bool): If true, existing translated files may be overwritten.

    Returns:
        tuple: (injects_result, stages)
            injects_result (dict): Summary of injection outcomes containing at least:
                - "saved_done" (int): number of files written.
                - "no_save" (int): number of files skipped.
                - "nested_files" (int): number of nested files encountered.
            stages (dict): The same stages object passed in, updated with final status and message.
    """
    if output_dir is None:
        stages["status"] = "Failed"
        stages["message"] = "inject task requires output_dir"
        return {}, stages
    # ---
    stages["message"] = f"inject 0/{len(files):,}"
    stages["status"] = "Running"
    # ---
    output_dir_translated = output_dir / "translated"
    output_dir_translated.mkdir(parents=True, exist_ok=True)
    # ---
    injects_result = start_injects(files, translations, output_dir_translated, overwrite=overwrite)
    # ---
    stages["message"] = f"inject ({len(files):,}) files: Done {injects_result['saved_done']:,}, Skipped {injects_result['no_save']:,}, nested files: {injects_result['nested_files']:,}"
    # ---
    stages["status"] = "Completed"
    # ---
    return injects_result, stages
