
from pathlib import Path
from tqdm import tqdm
import os
import sys
import json

from svg_translate import download_commons_svgs, get_files, get_wikitext, svg_extract_and_injects, extract, logger, config_logger, start_upload

from user_info import username, password

config_logger("CRITICAL")


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
            no_save += 1
            if stats.get("error") == "structure-error-nested-tspans-not-supported":
                nested_files += 1

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


def one_title_work(title, output_dir=None, titles_limit=None, overwrite=False):

    data = {
        "translations": {},
        "files": {},
        "saved_done": 0,
        "no_save": 0,
        "nested_files": 0,
    }
    text = get_wikitext(title)

    if not text:
        logger.error("NO TEXT")
        return None

    main_title, titles = get_files(text)

    if titles_limit and titles_limit > 0 and len(titles) > titles_limit:
        # use only n titles
        titles = titles[:titles_limit]

    data["main_title"] = main_title

    if not output_dir:
        output_dir = Path(__file__).parent.parent / "svg_data"
        if not os.getenv("HOME"):
            output_dir = Path("I:/SVG/svg_data")

    output_dir_main = output_dir / "files"
    output_dir_translated = output_dir / "translated"

    output_dir_main.mkdir(parents=True, exist_ok=True)
    output_dir_translated.mkdir(parents=True, exist_ok=True)

    files1 = download_commons_svgs([main_title], out_dir=output_dir_main)
    if not files1:
        logger.info(f"No files found for main title: {main_title}")
        return data

    main_title_path = files1[0]
    translations = extract(main_title_path, case_insensitive=True)

    data["translations"] = translations or {}

    if not translations:
        logger.info("No translations found for main title")
        return data

    translations_file = output_dir / "translations.json"

    with open(translations_file, "w", encoding="utf-8") as f:
        json.dump(translations, f, indent=4, ensure_ascii=False)

    files = download_commons_svgs(titles, out_dir=output_dir_main)

    injects_result = start_injects(files, translations, output_dir_translated, overwrite=overwrite)

    data.update(injects_result)

    files_stats_path = output_dir / "files_stats.json"

    with open(files_stats_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    logger.info(f"files_stats at: {files_stats_path}")

    return data


def one_title_web(title, output_dir, titles_limit=None, overwrite=False, do_upload=None):
    """
    Run the title workflow and return structured results suitable for a web UI.

    Returns a dict with keys:
    - title, output_dir
    - stages: list of {name, status, message}
    - results: summary numbers
    - files_to_upload: mapping of files prepared for upload (path present)
    - files_data: raw result from one_title_work (for diagnostics)
    - error: optional error string if a stage fails
    """

    stages = [
        {"name": "initialize", "status": "in_progress", "message": "Starting workflow"},
        {"name": "process-title", "status": "pending", "message": "Processing template and files"},
        {"name": "upload", "status": "pending", "message": "Uploading translated files"},
        {"name": "complete", "status": "pending", "message": "Finalizing"},
    ]

    result = {
        "title": title,
        "output_dir": str(output_dir),
        "stages": stages,
        "results": {},
        "files_to_upload": {},
        "files_data": None,
    }

    try:
        # Stage: initialize -> completed
        stages[0]["status"] = "completed"

        # Stage: process-title
        stages[1]["status"] = "in_progress"

        files_data = one_title_work(
            title, output_dir=output_dir, titles_limit=titles_limit, overwrite=overwrite
        )

        if not files_data:
            stages[1]["status"] = "error"
            stages[1]["message"] = "No data returned for title"
            result["error"] = "no files_data"
            return result

        result["files_data"] = files_data

        translations_new = files_data.get("translations", {}).get("new", {})

        # Prepare upload set and compute counts
        files_map = files_data.get("files") or {}
        if files_map:
            if files_data.get('main_title') in files_map:
                # exclude the main translation source file from uploads
                files_map = {k: v for k, v in files_map.items() if k != files_data['main_title']}

            files_to_upload = {x: v for x, v in files_map.items() if v.get("file_path")}
            no_file_path = len(files_map) - len(files_to_upload)
        else:
            files_to_upload = {}
            no_file_path = 0

        result["files_to_upload"] = files_to_upload

        # Summaries
        results_summary = {
            "total_files": len(files_map),
            "files_to_upload_count": len(files_to_upload),
            "no_file_path": no_file_path,
            "nested_files": files_data.get('nested_files', 0),
            "saved_done": files_data.get('saved_done', 0),
            "no_save": files_data.get('no_save', 0),
            "new_translations_count": len(translations_new),
            "main_title": files_data.get('main_title'),
        }
        result["results"] = results_summary

        stages[1]["status"] = "completed"
        stages[1]["message"] = (
            f"Processed {results_summary['total_files']} files; "
            f"to upload: {results_summary['files_to_upload_count']}"
        )

        # Stage: upload
        stages[2]["status"] = "in_progress" if files_to_upload else "completed"
        stages[2]["message"] = (
            "Uploading files" if files_to_upload else "No files to upload"
        )

        # Determine upload behavior
        if do_upload is None:
            # Preserve legacy behavior: upload unless 'noup' is in argv
            do_upload = ("noup" not in sys.argv)

        uploaded = []
        if files_to_upload and do_upload:
            try:
                main_title_link = f"[[:File:{files_data['main_title']}]]" if files_data.get('main_title') else ""
                start_upload(files_to_upload, main_title_link, username, password)
                stages[2]["status"] = "completed"
                stages[2]["message"] = f"Uploaded {len(files_to_upload)} files"
            except Exception as e:
                stages[2]["status"] = "error"
                stages[2]["message"] = f"Upload failed: {e}"
                result["error"] = f"upload-error: {e}"
        else:
            stages[2]["status"] = "completed"

        # Stage: complete
        stages[3]["status"] = "completed"
        stages[3]["message"] = (
            f"output_dir: {Path(output_dir).name}, "
            f"no_file_path: {results_summary['no_file_path']}, "
            f"nested: {results_summary['nested_files']}, "
            f"translations: {results_summary['new_translations_count']}"
        )

        return result

    except Exception as e:
        # Any uncaught error
        result["error"] = str(e)
        # Mark the first stage that is in progress as errored
        for st in stages:
            if st["status"] == "in_progress":
                st["status"] = "error"
                st["message"] = f"Error: {e}"
                break
        return result
