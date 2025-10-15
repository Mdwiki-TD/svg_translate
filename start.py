
from pathlib import Path

from commons.download_bot import download_commons_svgs
from commons.temps_bot import get_files
from commons.text_bot import get_wikitext

from svgpy.svgtranslate import svg_extract_and_injects
from svgpy.bots.extract_bot import extract


def start(title):

    text = get_wikitext(title)

    main_title, titles = get_files(text)

    # use only 10 titles
    titles = titles[:10]

    titles2 = titles
    titles2.append(main_title)

    output_dir = Path(__file__).parent / "new_data/files"
    output_dir_translated = Path(__file__).parent / "new_data/translated"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir_translated.mkdir(parents=True, exist_ok=True)

    files = download_commons_svgs(titles2, out_dir=output_dir)

    translations = extract(output_dir / main_title, case_insensitive=True)

    if not translations:
        print("No translations found for main title")
        return

    for n, file in enumerate(files):
        # ---
        if file.name == main_title:
            continue
        # ---
        tree, stats = svg_extract_and_injects(translations, file, save_result=False, return_stats=True)

        print(f"Processed {stats['processed_switches']} switches")
        print(f"Inserted {stats['inserted_translations']} translations")
        print(f"Updated {stats['updated_translations']} translations")
        print(f"Skipped {stats['skipped_translations']} existing translations")

        output_file = output_dir_translated / file.name
        if tree:
            tree.write(str(output_file), encoding='utf-8', xml_declaration=True, pretty_print=True)
        else:
            print(f"Failed to translate {file.name}")

        if n == 10:
            break


if __name__ == "__main__":
    title = "Template:OWID/Parkinsons prevalence"
    start(title)
