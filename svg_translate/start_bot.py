
from pathlib import Path
from tqdm import tqdm
import json

from .commons.download_bot import download_commons_svgs
from .commons.temps_bot import get_files
from .commons.text_bot import get_wikitext

from .svgpy.svgtranslate import svg_extract_and_injects
from .svgpy.bots.extract_bot import extract

from .log import logger, config_logger

# config_logger("CRITICAL")


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


def one_title(title, output_dir=None, titles_limit=None, overwrite=False):
    workflow = []

    def add_stage(stage, status, message, **kwargs):
        workflow.append({"stage": stage, "status": status, "message": message, **kwargs})

    try:
        add_stage("Fetching wikitext", "in_progress", f"Fetching wikitext for title: {title}")
        text = get_wikitext(title)
        if not text:
            add_stage("Fetching wikitext", "failed", "No wikitext found for this title.")
            return workflow
        add_stage("Fetching wikitext", "completed", "Wikitext fetched successfully.")

        add_stage("Parsing files", "in_progress", "Parsing files from wikitext.")
        main_title, titles = get_files(text)
        if titles_limit and titles_limit > 0:
            titles = titles[:titles_limit]
        add_stage("Parsing files", "completed", f"Found main title '{main_title}' and {len(titles)} other files.")

        if not output_dir:
            output_dir = Path(__file__).parent / "new_data"
        output_dir_main = output_dir / "files"
        output_dir_translated = output_dir / "translated"
        output_dir_main.mkdir(parents=True, exist_ok=True)
        output_dir_translated.mkdir(parents=True, exist_ok=True)

        add_stage("Downloading main file", "in_progress", f"Downloading {main_title}.")
        files1 = download_commons_svgs([main_title], out_dir=output_dir_main)
        if not files1:
            add_stage("Downloading main file", "failed", f"Could not download main file: {main_title}.")
            return workflow
        main_title_path = files1[0]
        add_stage("Downloading main file", "completed", f"Successfully downloaded {main_title}.")

        add_stage("Extracting translations", "in_progress", "Extracting translations from the main file.")
        translations = extract(main_title_path, case_insensitive=True)
        if not translations:
            add_stage("Extracting translations", "failed", "No translations found in the main file.")
            return workflow
        add_stage("Extracting translations", "completed", f"Found {len(translations)} translations.", translations=translations)

        add_stage("Downloading other files", "in_progress", f"Downloading {len(titles)} other files.")
        files = download_commons_svgs(titles, out_dir=output_dir_main)
        add_stage("Downloading other files", "completed", f"Successfully downloaded {len(files)} files.")

        add_stage("Injecting translations", "in_progress", f"Injecting translations into {len(files)} files.")
        injects_result = start_injects(files, translations, output_dir_translated, overwrite=overwrite)
        add_stage("Injecting translations", "completed", "Finished injecting translations.", **injects_result)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        add_stage("Error", "failed", f"An unexpected error occurred: {str(e)}")

    return workflow
