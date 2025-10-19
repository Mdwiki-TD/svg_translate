
import json

from .commons.download_bot import download_commons_svgs
from .commons.temps_bot import get_files
from .commons.text_bot import get_wikitext

from .injects_files import start_injects
from .svgpy.bots.extract_bot import extract

from .log import logger  # , config_logger
# config_logger("CRITICAL")


def start_on_template_title(title, output_dir=None, titles_limit=None, overwrite=False):

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

    if not main_title:
        logger.error("No main SVG title found in the template")
        return data

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
