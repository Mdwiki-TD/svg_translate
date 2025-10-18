
# from pathlib import Path
# import os
# import sys
from tqdm import tqdm
import json
import html
from urllib.parse import quote

from svg_translate import download_commons_svgs, get_files, get_wikitext, svg_extract_and_injects, extract, logger, config_logger, start_upload
from user_info import username, password

# config_logger("CRITICAL")
config_logger("DEBUG")


def json_save(path, data):

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

    except (OSError, TypeError, ValueError) as e:
        logger.error(f"Error saving json: {e}")
    except Exception as e:
        logger.error(f"Error saving json: {e}")


def commons_link(title, name=None):
    safe_name = html.escape(name or title, quote=True)
    href = f"https://commons.wikimedia.org/wiki/{quote(title, safe='/:()')}"
    return f"<a href='{href}' target='_blank' rel='noopener noreferrer'>{safe_name}</a>"


def save_files_stats(data, output_dir):

    files_stats_path = output_dir / "files_stats.json"
    json_save(files_stats_path, data)

    logger.info(f"files_stats at: {files_stats_path}")


def make_results_summary(files, files_to_upload, no_file_path, injects_result, translations, main_title, upload_result):
    return {
        "total_files": len(files),
        "files_to_upload_count": len(files_to_upload),
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


def start_injects(files, translations, output_dir_translated, overwrite=False):

    saved_done = 0
    no_save = 0
    nested_files = 0

    files_stats = {}
    # new_data_paths = {}

    # files = list(set(files))

    for _n, file in tqdm(enumerate(files, 1), total=len(files), desc="Inject files:"):
        # ---
        tree, stats = svg_extract_and_injects(translations, file, save_result=False, return_stats=True, overwrite=overwrite)
        stats["file_path"] = ""

        output_file = output_dir_translated / file.name

        if tree:
            # new_data_paths[file.name] = str(output_file)
            stats["file_path"] = str(output_file)
            tree.write(str(output_file), encoding='utf-8', xml_declaration=True, pretty_print=True)
            saved_done += 1
        else:
            # logger.error(f"Failed to translate {file.name}")
            if stats.get("error") == "structure-error-nested-tspans-not-supported":
                nested_files += 1
            else:
                no_save += 1

        files_stats[file.name] = stats
        # if n == 10: break

    logger.info(f"all files: {len(files):,} Saved {saved_done:,}, skipped {no_save:,}, nested_files: {nested_files:,}")

    data = {
        "saved_done": saved_done,
        "no_save": no_save,
        "nested_files": nested_files,
        "files": files_stats,
    }

    return data


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

    return main_title, titles, stages


def translations_task(stages, main_title, output_dir_main):
    # ---
    stages["message"] = f"Load translations from main file {main_title}"
    # ---
    stages["sub_name"] = commons_link(f'File:{main_title}')
    # ---
    # stages["message"] = f"Load translations from main file <a href='https://commons.wikimedia.org/wiki/File:{main_title}' target='_blank'>File:{main_title}</a>"
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
    stages["message"] = f"Loaded {len(translations):,} translations from main file"
    # ---
    return translations, stages


def download_task(stages, output_dir_main, titles):
    # ---
    stages["message"] = f"Downloading 0/{len(titles):,}"
    stages["status"] = "Running"
    # ---
    files = download_commons_svgs(titles, out_dir=output_dir_main)
    # ---
    logger.info(f"files: {len(files)}")
    # ---
    stages["message"] = f"Downloaded {len(titles):,}/{len(titles):,}"
    stages["status"] = "Completed"
    # ---
    return files, stages


def inject_task(stages, files, translations, output_dir=None, overwrite=False):
    # ---
    if output_dir is None:
        stages["status"] = "Failed"
        stages["message"] = "inject_task requires output_dir"
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


def upload_task(stages, files_to_upload, main_title, do_upload=None):
    # ---
    stages["status"] = "Running"
    # ---
    stages["message"] = f"Uploading files 0/{len(files_to_upload):,}"
    # ---
    if not do_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (Upload disabled)"
        return {"done": 0, "not_done": len(files_to_upload), "skipped": True, "reason": "disabled"}, stages
    # ---
    if not files_to_upload:
        stages["status"] = "Skipped"
        stages["message"] += " (No files to upload)"
        return {"done": 0, "not_done": 0, "skipped": True, "reason": "no-input"}, stages
    # ---
    main_title_link = f"[[:File:{main_title}]]"
    # ---
    if not username or not password:
        stages["status"] = "Failed"
        stages["message"] += " (Missing credentials)"
        return {"done": 0, "not_done": len(files_to_upload), "skipped": True, "reason": "missing-creds"}, stages
    # ---
    upload_result = start_upload(files_to_upload, main_title_link, username, password)
    # ---
    stages["message"] = (
        f"Total Files: {len(files_to_upload):,}, "
        f"Files uploaded {upload_result['done']:,}, "
        f"Files not uploaded: {upload_result['not_done']:,}"
    )
    # ---
    stages["status"] = "Completed"
    # ---
    return upload_result, stages
