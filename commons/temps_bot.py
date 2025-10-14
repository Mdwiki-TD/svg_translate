"""

read temp.txt
get main title from {{SVGLanguages|parkinsons-disease-prevalence-ihme,World,1990.svg}} using wtp
get all files names from owidslidersrcs

"""


from pathlib import Path
import wikitextparser as wtp
import re


Dir = Path(__file__).parent


def get_files(text):
    """
    Extracts:
      - main_title from {{SVGLanguages|...}}
      - all file names from {{owidslidersrcs}}
    Returns: (main_title, titles)
    """

    # Parse the text using wikitextparser
    parsed = wtp.parse(text)

    # --- 1. Extract main title from {{SVGLanguages|...}}
    main_title = None
    for tpl in parsed.templates:
        if tpl.name.strip().lower() == "svglanguages":
            if tpl.arguments:
                main_title = tpl.arguments[0].value.strip()
            break

    # --- 2. Extract all file names from {{owidslidersrcs|...}}
    titles = []
    for tpl in parsed.templates:
        if tpl.name.strip().lower() == "owidslidersrcs":
            # Find all filenames inside this template
            matches = re.findall(r"File:([^\n|!]+\.svg)", tpl.string)
            titles.extend(m.strip() for m in matches)
    return main_title, titles


if __name__ == "__main__":
    text = (Dir / "temp.txt").read_text(encoding="utf-8")
    main_title, titles = get_files(text)

    print("Main title:", main_title)
    print("Files count:", len(titles))
    print("First 5 files:", titles[:5])
