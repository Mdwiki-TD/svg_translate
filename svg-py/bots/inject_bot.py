#!/usr/bin/env python3
"""

python I:/mdwiki/pybot/svg/svg-py/bots/inject_bot.py

"""

import json
import logging
from pathlib import Path
from lxml import etree

# from .utils import normalize_text, extract_text_from_node
from .translation_ready import make_translation_ready

logger = logging.getLogger(__name__)


def normalize_text(text):
    """Normalize text by trimming whitespace and collapsing internal whitespace."""
    if not text:
        return ""
    # Trim leading/trailing whitespace
    text = text.strip()
    # Replace multiple internal whitespace with single space
    text = ' '.join(text.split())
    return text


def extract_text_from_node(node):
    """Extract text from a text node, handling tspan elements."""
    # Try to find tspan elements first
    tspans = node.xpath('./svg:tspan', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    if tspans:
        # Return a list of text from each tspan element
        return [tspan.text.strip() if tspan.text else "" for tspan in tspans]
    # Fall back to direct text content
    return [node.text.strip()] if node.text else [""]


def generate_unique_id(base_id, lang, existing_ids):
    """Generate a unique ID by appending language code and numeric suffix if needed."""
    new_id = f"{base_id}-{lang}"

    # If the base ID with language is unique, use it
    if new_id not in existing_ids:
        return new_id

    # Otherwise, add numeric suffix until unique
    counter = 1
    while f"{new_id}-{counter}" in existing_ids:
        counter += 1

    return f"{new_id}-{counter}"


def load_all_mappings(mapping_files):
    all_mappings = {}

    for mapping_file in mapping_files:
        mapping_file = Path(mapping_file)
        if not mapping_file.exists():
            logger.warning(f"Mapping file not found: {mapping_file}")
            continue

        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)

            # Merge mappings
            for key, value in mappings.items():
                if key not in all_mappings:
                    all_mappings[key] = {}
                all_mappings[key].update(value)

            logger.info(f"Loaded mappings from {mapping_file}, len: {len(mappings)}")
        except Exception as e:
            logger.error(f"Error loading mapping file {mapping_file}: {str(e)}")

    return all_mappings


def work_on_switches(root, existing_ids, all_mappings, case_insensitive=False, overwrite=False):
    stats = {
        'processed_switches': 0,
        'inserted_translations': 0,
        'skipped_translations': 0,
        'updated_translations': 0
    }

    switches = root.xpath('//svg:switch', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    logger.info(f"Found {len(switches)} switch elements")

    if not switches:
        logger.error("No switch elements found in SVG")

    # Assume data structure like: {"new": {"english": {"ar": "..."}}}
    # Extract that level once
    all_mappings = all_mappings.get("new", all_mappings)

    for switch in switches:
        text_elements = switch.xpath('./svg:text', namespaces={'svg': 'http://www.w3.org/2000/svg'})
        if not text_elements:
            continue

        default_texts = None
        default_node = None

        for text_elem in text_elements:
            system_lang = text_elem.get('systemLanguage')
            if not system_lang:
                text_contents = extract_text_from_node(text_elem)
                default_texts = [normalize_text(text) for text in text_contents]
                if case_insensitive:
                    default_texts = [text.lower() for text in default_texts]
                default_node = text_elem
                break

        if not default_texts:
            continue

        # Determine translations for each text line
        available_translations = {}
        for text in default_texts:
            key = text.lower() if case_insensitive else text
            if key in all_mappings:
                available_translations[key] = all_mappings[key]
            else:
                logger.debug(f"No mapping for '{key}'")

        if not available_translations:
            continue

        existing_languages = {t.get('systemLanguage') for t in text_elements if t.get('systemLanguage')}

        # We assume all texts share same set of languages
        all_langs = set()
        for data in available_translations.values():
            all_langs.update(data.keys())

        for lang in all_langs:
            if lang in existing_languages and not overwrite:
                stats['skipped_translations'] += 1
                continue

            # Create or update node
            if lang in existing_languages and overwrite:
                for text_elem in text_elements:
                    if text_elem.get('systemLanguage') == lang:
                        tspans = text_elem.xpath('./svg:tspan', namespaces={'svg': 'http://www.w3.org/2000/svg'})
                        for i, tspan in enumerate(tspans):
                            eng_text = default_texts[i]
                            if eng_text in available_translations and lang in available_translations[eng_text]:
                                tspan.text = available_translations[eng_text][lang]
                        stats['updated_translations'] += 1
                        break
            else:
                new_node = etree.Element(default_node.tag, attrib=default_node.attrib)
                new_node.set('systemLanguage', lang)
                original_id = default_node.get('id')
                if original_id:
                    new_id = generate_unique_id(original_id, lang, existing_ids)
                    new_node.set('id', new_id)
                    existing_ids.add(new_id)

                tspans = default_node.xpath('./svg:tspan', namespaces={'svg': 'http://www.w3.org/2000/svg'})

                if tspans:
                    for tspan in tspans:
                        new_tspan = etree.Element(tspan.tag, attrib=tspan.attrib)
                        eng_text = normalize_text(tspan.text or "")
                        key = eng_text.lower() if case_insensitive else eng_text
                        translated = all_mappings.get(key, {}).get(lang, eng_text)
                        new_tspan.text = translated

                        # Generate unique ID for tspan if needed
                        original_tspan_id = tspan.get('id')
                        if original_tspan_id:
                            new_tspan_id = generate_unique_id(original_tspan_id, lang, existing_ids)
                            new_tspan.set('id', new_tspan_id)
                            existing_ids.add(new_tspan_id)

                        new_node.append(new_tspan)

                else:
                    eng_text = normalize_text(default_node.text or "")
                    key = eng_text.lower() if case_insensitive else eng_text
                    translated = all_mappings.get(key, {}).get(lang, eng_text)
                    new_node.text = translated

                switch.insert(0, new_node)
                stats['inserted_translations'] += 1

        stats['processed_switches'] += 1

    return stats


def sort_switch_texts(elem):
    """
    Sort <text> elements inside each <switch> so that elements
    without systemLanguage attribute come last.
    """
    ns = {"svg": "http://www.w3.org/2000/svg"}

    # Iterate over all <switch> elements
    # Get all <text> elements
    texts = elem.findall("svg:text", namespaces=ns)

    # Separate those with systemLanguage and those without
    without_lang = [t for t in texts if t.get("systemLanguage") is None]

    # Clear switch content
    for t in without_lang:
        elem.remove(t)

    # Re-insert <text> elements: first with language, then without
    for t in without_lang:
        elem.append(t)

    return elem


def inject(svg_file_path, mapping_files=None, output_file=None, output_dir=None, overwrite=False, case_insensitive=True, all_mappings=None):
    """
    Inject translations into an SVG file based on mapping files.

    Args:
        svg_file_path: Path to the SVG file to inject translations into
        mapping_files: List of paths to JSON mapping files
        output_dir: Directory to save modified SVG files (defaults to same directory as input)
        overwrite: Whether to overwrite existing translations
        case_insensitive: Whether to normalize case when matching strings

    Returns:
        Dictionary with statistics about the injection process
    """

    svg_file_path = Path(svg_file_path)

    if not svg_file_path.exists():
        logger.error(f"SVG file not found: {svg_file_path}")
        return None

    if not all_mappings and mapping_files:
        # Load all mapping files
        all_mappings = load_all_mappings(mapping_files)

    if not all_mappings:
        logger.error("No valid mappings found")
        return None

    logger.info(f"Injecting translations into {svg_file_path}")

    # Parse SVG as XML
    # parser = etree.XMLParser(remove_blank_text=True)
    # tree = etree.parse(str(svg_file_path), parser)
    # root = tree.getroot()

    tree, root = make_translation_ready(svg_file_path)
    # Find all switch elements

    # Collect all existing IDs to ensure uniqueness
    existing_ids = set(root.xpath('//@id'))

    stats = work_on_switches(root, existing_ids, all_mappings, case_insensitive=case_insensitive, overwrite=overwrite)

    # Fix old <svg:switch> tags if present
    for elem in root.findall(".//svg:switch", namespaces={"svg": "http://www.w3.org/2000/svg"}):
        elem.tag = "switch"
        sort_switch_texts(elem)

    if not output_file and output_dir:
        output_file = output_dir / svg_file_path.name

    # Write the modified SVG
    tree.write(str(output_file), encoding='utf-8', xml_declaration=True, pretty_print=True)

    logger.info(f"Saved modified SVG to {output_file}")

    logger.info(f"Processed {stats['processed_switches']} switches")
    logger.info(f"Inserted {stats['inserted_translations']} translations")
    logger.info(f"Updated {stats['updated_translations']} translations")
    logger.info(f"Skipped {stats['skipped_translations']} existing translations")

    return tree
