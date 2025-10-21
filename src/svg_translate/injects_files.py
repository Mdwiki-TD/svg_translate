
from tqdm import tqdm
from pathlib import Path
import logging

from .svgpy.svgtranslate import svg_extract_and_injects
logger = logging.getLogger(__name__)


def start_injects(files, translations, output_dir_translated, overwrite=False):
    """Inject translations into multiple SVG files and write the results.

    Parameters:
        files (Iterable[pathlib.Path | str]): Source SVG paths to process.
        translations (dict): Mapping of translation data understood by
            :func:`svg_translate.svgpy.bots.inject_bot.inject`.
        output_dir_translated (pathlib.Path): Destination directory for translated
            SVG files; the directory must be writable and will receive one file per
            source entry.
        overwrite (bool): Whether to allow inject_bot to overwrite existing
            translations within the SVG content.

    Returns:
        dict: Aggregated statistics keyed by `saved_done`, `no_save`,
        `nested_files`, and `files` (per-file outcome mapping).
    """

    saved_done = 0
    no_save = 0
    nested_files = 0

    files_stats = {}
    # new_data_paths = {}

    # files = list(set(files))

    for _n, file in tqdm(enumerate(files, 1), total=len(files), desc="Inject files:"):
        # ---
        file = Path(str(file))
        # ---
        tree, stats = svg_extract_and_injects(translations, file, save_result=False, return_stats=True, overwrite=overwrite)
        stats["file_path"] = ""

        output_file = output_dir_translated / file.name

        if not tree:
            # logger.error(f"Failed to translate {file.name}")
            if stats.get("error") == "structure-error-nested-tspans-not-supported":
                nested_files += 1
            else:
                no_save += 1
            files_stats[file.name] = stats
            continue
        # ---
        try:
            tree.write(str(output_file), encoding='utf-8', xml_declaration=True, pretty_print=True)
            # ---
            # new_data_paths[file.name] = str(output_file)
            stats["file_path"] = str(output_file)
            # ---
            saved_done += 1
        except Exception as e:
            logger.error(f"Failed writing {output_file}: {e}")
            # ---
            stats["error"] = "write-failed"
            stats["file_path"] = ""
            # ---
            tree = None
            # ---
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
