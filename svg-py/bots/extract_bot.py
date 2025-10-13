#!/usr/bin/env python3
"""

python I:/mdwiki/pybot/svg/svg-py/bots/extract_bot.py

"""

import json
import logging
from pathlib import Path
from lxml import etree

from .utils import normalize_text, extract_text_from_node

logger = logging.getLogger(__name__)


def extract(svg_file_path, case_insensitive=True):
    """
    Extract translations from an SVG file and save them as JSON.

    Args:
        svg_file_path: Path to the SVG file to extract translations from
        case_insensitive: Whether to normalize case when matching strings

    Returns:
        Dictionary containing the extracted translations
    """
    svg_file_path = Path(svg_file_path)

    if not svg_file_path.exists():
        logger.error(f"SVG file not found: {svg_file_path}")
        return None

    logger.info(f"Extracting translations from {svg_file_path}")

    # Parse SVG as XML
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(svg_file_path), parser)
    root = tree.getroot()

    # Find all switch elements
    switches = root.xpath('//svg:switch', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    logger.info(f"Found {len(switches)} switch elements")

    translations = {}
    translations["new"] = {}
    translations["new"]["default_tspans_by_id"] = {}
    processed_switches = 0

    for switch in switches:
        # Find all text elements within this switch
        text_elements = switch.xpath('./svg:text', namespaces={'svg': 'http://www.w3.org/2000/svg'})

        if not text_elements:
            continue

        # Identify default text (no systemLanguage attribute)
        default_text = None
        default_node = None

        # Find translations
        switch_translations = {}

        for text_elem in text_elements:
            system_lang = text_elem.get('systemLanguage')
            # ---
            tspans = text_elem.xpath('./svg:tspan', namespaces={'svg': 'http://www.w3.org/2000/svg'})
            # ---
            tspans_by_id = {}
            tspans_to_id = {}
            # ---
            if tspans:
                # Return a list of text from each tspan element
                text_contents = [tspan.text.strip() if tspan.text else "" for tspan in tspans]
                tspans_by_id = {tspan.get('id'): tspan.text.strip() for tspan in tspans if tspan.text}
                tspans_to_id = {span: id for id, span in tspans_by_id.items()}
            else:
                text_contents = [text_elem.text.strip()] if text_elem.text else [""]
            # ---
            if not system_lang:
                translations["new"]["default_tspans_by_id"].update(tspans_by_id)
                # This is the default text
                default_texts = [normalize_text(text, case_insensitive) for text in text_contents]
                # ---
                for text in default_texts:
                    text2 = text.lower() if case_insensitive else text
                    if text2 not in translations["new"]:
                        translations["new"][text2] = {}
                # ---
            else:
                # This is a translation
                normalized_contents = [normalize_text(text) for text in text_contents]
                # ---
                switch_translations[system_lang] = normalized_contents
                # ---
                for text in text_contents:
                    # ---
                    text_ar = normalize_text(text)
                    # ---
                    en_key = tspans_to_id.get(text.strip(), "").split("-")[0].strip()
                    # ---
                    en_key = en_key.lower() if case_insensitive else en_key
                    # ---
                    print(en_key)
                    # ---
                    if translations["new"]["default_tspans_by_id"].get(en_key):
                        en_text = translations["new"]["default_tspans_by_id"][en_key]
                        translations["new"][en_text][system_lang] = text_ar

        # If we found both default text and translations, add to our data
        if default_texts and switch_translations:
            # Create a key from the first default text (we could use all texts but this is simpler)
            default_key = default_texts[0]

            if default_key not in translations:
                translations[default_key] = {
                    '_texts': default_texts,  # Store all default texts
                    '_translations': {}      # Store translations for each text
                }

            # Store translations for each language and each text
            for lang, translated_texts in switch_translations.items():
                translations[default_key]['_translations'][lang] = translated_texts

            processed_switches += 1
            logger.debug(f"Processed switch with default texts: {default_texts}")

    logger.info(f"Extracted translations for {processed_switches} switches")

    # Count languages
    all_languages = set()
    for text_dict in translations.values():
        all_languages.update(text_dict.keys())

    logger.info(f"Found translations in {len(all_languages)} languages: {', '.join(sorted(all_languages))}")

    return translations
