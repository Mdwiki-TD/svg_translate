
# from pathlib import Path
# import os
# import sys
from tqdm import tqdm
import json

from svg_translate import download_commons_svgs, get_files, get_wikitext, svg_extract_and_injects, extract, logger, config_logger, start_upload

from user_info import username, password

config_logger("CRITICAL")


def json_save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving json: {e}")


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

    for n, file in tqdm(enumerate(files, 1), total=len(files), desc="Inject files:"):
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

    stages["status"] = "in_progress"

    text = get_wikitext(title)

    if not text:
        stages["status"] = "Error"
        logger.error("NO TEXT")
    else:
        stages["status"] = "Completed"
    return text, stages


def titles_task(stages, text, titles_limit=None):

    stages["status"] = "in_progress"

    main_title, titles = get_files(text)

    if not titles:
        stages["status"] = "Error"
        logger.error("NO TEXT")
    else:
        stages["status"] = "Completed"

    if titles_limit and titles_limit > 0 and len(titles) > titles_limit:
        # use only n titles
        titles = titles[:titles_limit]

    return main_title, titles, stages


def translations_task(stages, main_title, output_dir_main):
    # ---
    stages["message"] = f"Load translations from main file {main_title}"
    stages["status"] = "in_progress"
    # ---
    files1 = download_commons_svgs([main_title], out_dir=output_dir_main)
    if not files1:
        logger.info(f"No files found for main title: {main_title}")
        stages["status"] = "Error"
        return {}, stages

    main_title_path = files1[0]
    translations = extract(main_title_path, case_insensitive=True)

    if not translations:
        logger.info("No translations found for main title")
        stages["status"] = "Error"
        return translations, stages

    json_save(output_dir_main.parent / "translations.json", translations)

    stages["status"] = "Completed"
    # ---
    return translations, stages


def download_task(stages, output_dir_main, titles):
    # ---
    stages["message"] = f"Downloading 0/{len(titles):,}"
    stages["status"] = "in_progress"
    # ---
    files = download_commons_svgs(titles, out_dir=output_dir_main)
    # ---
    logger.info(f"files: {len(files)}")
    # ---
    stages["message"] = f"Downloading {len(titles):,}/{len(titles):,}"
    stages["status"] = "Completed"
    # ---
    return files, stages


def inject_task(stages, files, translations, output_dir=None, overwrite=False):
    # ---
    stages["message"] = f"inject 0/{len(files):,}"
    stages["status"] = "in_progress"
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
    if not files_to_upload or not do_upload:
        stages["status"] = "Completed"
        stages["message"] = "No files to upload" if not files_to_upload else "Upload disabled"
        return {}, stages
    # ---
    stages["message"] = f"Uploading files 0/{len(files_to_upload):,}"
    stages["status"] = "in_progress"
    # ---
    main_title_link = f"[[:File:{main_title}]]"
    # ---
    upload_result = start_upload(files_to_upload, main_title_link, username, password)
    # ---
    stages["message"] = f"Total: {len(files_to_upload):,}, Done {upload_result['done']:,}, False: {upload_result['not_done']:,}"
    stages["status"] = "Completed"
    # ---
    return upload_result, stages
