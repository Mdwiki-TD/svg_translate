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


def extract(svg_file_path, data_output_file, case_insensitive=True):
    """
    Extract translations from an SVG file and save them as JSON.

    Args:
        svg_file_path: Path to the SVG file to extract translations from
        data_output_file: Path to save the JSON output (defaults to <svg_file_path>.json)
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
            text_contents = extract_text_from_node(text_elem)

            if not system_lang:
                # This is the default text
                default_texts = [normalize_text(text) for text in text_contents]
                if case_insensitive:
                    default_texts = [text.lower() for text in default_texts]
                default_node = text_elem
            else:
                # This is a translation
                normalized_contents = [normalize_text(text) for text in text_contents]
                if case_insensitive:
                    normalized_contents = [text.lower() for text in normalized_contents]
                switch_translations[system_lang] = normalized_contents

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

    # Save translations to JSON
    with open(data_output_file, 'w', encoding='utf-8') as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)

    logger.info(f"Extracted translations for {processed_switches} switches")
    logger.info(f"Saved translations to {data_output_file}")

    # Count languages
    all_languages = set()
    for text_dict in translations.values():
        all_languages.update(text_dict.keys())

    logger.info(f"Found translations in {len(all_languages)} languages: {', '.join(sorted(all_languages))}")

    return translations
