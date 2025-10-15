
from pathlib import Path
from tqdm import tqdm
import json

from commons.download_bot import download_commons_svgs
from commons.temps_bot import get_files
from commons.text_bot import get_wikitext

from svgpy.svgtranslate import svg_extract_and_injects
from svgpy.bots.extract_bot import extract


def start_injects(files, translations, output_dir_translated, overwrite=False):

    saved_done = 0
    no_save = 0

    files_stats = {}
    # new_data_paths = {}

    # files = list(set(files))

    for n, file in tqdm(enumerate(files, 1), total=len(files), desc="Inject files:"):
        # ---
        tree, stats = svg_extract_and_injects(translations, file, save_result=False, return_stats=True, overwrite=overwrite)

        output_file = output_dir_translated / file.name

        if tree:
            # new_data_paths[file.name] = str(output_file)
            stats["file_path"] = str(output_file)
            tree.write(str(output_file), encoding='utf-8', xml_declaration=True, pretty_print=True)
            saved_done += 1
        else:
            print(f"Failed to translate {file.name}")
            no_save += 1

        files_stats[file.name] = stats
        # if n == 10: break

    print(f"all files: {len(files):,} Saved {saved_done:,}, skipped {no_save:,}")

    return files_stats  # , new_data_paths


def start_on_template_title(title, output_dir=None, titles_limit=None, overwrite=False):
    data = {}
    text = get_wikitext(title)

    main_title, titles = get_files(text)

    if titles_limit and titles_limit.is_integer() and len(titles) < titles_limit:
        # use only n titles
        titles = titles[:titles_limit]

    data["main_title"] = main_title

    if not output_dir:
        output_dir = Path(__file__).parent / "new_data"

    output_dir_main = output_dir / "files"
    output_dir_translated = output_dir / "translated"

    output_dir_main.mkdir(parents=True, exist_ok=True)
    output_dir_translated.mkdir(parents=True, exist_ok=True)

    files1 = download_commons_svgs([main_title], out_dir=output_dir_main)
    if not files1:
        print(f"No files found for main title: {main_title}")
        return data

    main_title_path = files1[0]
    translations = extract(main_title_path, case_insensitive=True)

    if not translations:
        print("No translations found for main title")
        return data

    files = download_commons_svgs(titles, out_dir=output_dir_main)

    data["files"] = start_injects(files, translations, output_dir_translated, overwrite=overwrite)

    files_stats_path = output_dir / "files_stats.json"

    with open(files_stats_path, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"files_stats at: {files_stats_path}")

    return data
