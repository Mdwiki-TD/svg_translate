"""

read temp.txt
get main title from {{SVGLanguages|parkinsons-disease-prevalence-ihme,World,1990.svg}} using wtp
get all files names from owidslidersrcs

"""

import wikitextparser as wtp
import re


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

    if main_title:
        main_title = main_title.replace("_", " ").strip()

    return main_title, titles
