#!/usr/bin/env python3
"""

python I:/SVG/svg_repo/svgpy/bots/inject_bot.py

"""

import json
from pathlib import Path
from lxml import etree

from .utils import normalize_text, extract_text_from_node
from .translation_ready import make_translation_ready
from ...log import logger


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
    """Load and merge translation mapping JSON files into a single dictionary.

    Parameters:
        mapping_files (Iterable[pathlib.Path | str]): Paths to JSON files whose
            contents map source text to language translations.

    Returns:
        dict: Nested dictionary where the top-level keys correspond to source
        strings and values are language-to-translation mappings. Files that fail
        to load are skipped with a logged warning.
    """
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


def work_on_switches(root, existing_ids, mappings, case_insensitive=False,
                     overwrite=False):
    """Process SVG switch elements for internationalization.

    Args:
        root: XML root element
        existing_ids: Set of existing IDs to avoid duplicates
        mappings: Dictionary of translations
        case_insensitive: Whether to ignore case in text matching
        overwrite: Whether to update existing translations

    Returns:
        Dictionary of processing statistics
    """
    SVG_NS = {'svg': 'http://www.w3.org/2000/svg'}
    stats = {
        'all_languages': 0,
        'new_languages': 0,
        'processed_switches': 0,
        'inserted_translations': 0,
        'skipped_translations': 0,
        'updated_translations': 0
    }

    switches = root.xpath('//svg:switch', namespaces=SVG_NS)
    logger.info(f"Found {len(switches)} switch elements")

    if not switches:
        logger.error("No switch elements found in SVG")

    # Assume data structure like: {"new": {"english": {"ar": "..."}}}
    # Extract that level once
    all_mappings_title = mappings.get("title", {})
    all_mappings = mappings.get("new", mappings)

    all_languages = set()
    new_languages = set()

    for switch in switches:
        text_elements = switch.xpath('./svg:text', namespaces=SVG_NS)
        if not text_elements:
            continue

        default_texts = None
        default_node = None

        for text_elem in text_elements:
            system_lang = text_elem.get('systemLanguage')
            if not system_lang:
                text_contents = extract_text_from_node(text_elem)
                default_texts = [normalize_text(text, case_insensitive) for text in text_contents]
                default_node = text_elem
                break

        if not default_texts:
            continue

        for x in default_texts:
            if x[-4:].isdigit():
                year = x[-4:]
                key = x[:-4]
                if key in all_mappings_title:
                    tr = all_mappings_title[key]
                    all_mappings[x] = {lang: f"{tr[lang]} {year}" for lang in tr.keys()}

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
        all_languages.update(existing_languages)

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
                        tspans = text_elem.xpath('./svg:tspan', namespaces=SVG_NS)
                        for i, tspan in enumerate(tspans):
                            # ---
                            eng_text = default_texts[i]
                            # ---
                            lookup_key = eng_text.lower() if case_insensitive else eng_text
                            # ---
                            if eng_text in available_translations and lang in available_translations[eng_text]:
                                tspan.text = available_translations[eng_text][lang]
                            # ---
                            elif lookup_key in available_translations and lang in available_translations[lookup_key]:
                                tspan.text = available_translations[lookup_key][lang]
                        # ---
                        stats['updated_translations'] += 1
                        break
            else:
                new_languages.add(lang)

                new_node = etree.Element(default_node.tag, attrib=default_node.attrib)
                new_node.set('systemLanguage', lang)
                original_id = default_node.get('id')
                if original_id:
                    new_id = generate_unique_id(original_id, lang, existing_ids)
                    new_node.set('id', new_id)
                    existing_ids.add(new_id)

                tspans = default_node.xpath('./svg:tspan', namespaces=SVG_NS)

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

    stats["all_languages"] = len(all_languages)
    stats["new_languages"] = len(new_languages)

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


def _inject(svg_file_path, mapping_files=None, output_file=None, output_dir=None, overwrite=False,
            case_insensitive=True, all_mappings=None, save_result=False
            , **kwargs):
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
        return None, {"error": "File not exists"}

    if not all_mappings and mapping_files:
        # Load all mapping files
        all_mappings = load_all_mappings(mapping_files)

    if not all_mappings:
        logger.error("No valid mappings found")
        return None, {"error": "No valid mappings found"}

    logger.info(f"Injecting translations into {svg_file_path}")

    # Parse SVG as XML
    # parser = etree.XMLParser(remove_blank_text=True)
    # tree = etree.parse(str(svg_file_path), parser)
    # root = tree.getroot()
    try:
        tree, root = make_translation_ready(svg_file_path)
    except Exception as e:
        if str(e) != "structure-error-nested-tspans-not-supported":
            logger.error(f"Failed to parse SVG file: {e}")
        return None, {"error": str(e)}
    # Find all switch elements

    # Collect all existing IDs to ensure uniqueness
    existing_ids = set(root.xpath('//@id'))

    stats = work_on_switches(root, existing_ids, all_mappings, case_insensitive=case_insensitive, overwrite=overwrite)

    # Fix old <svg:switch> tags if present
    for elem in root.findall(".//svg:switch", namespaces={"svg": "http://www.w3.org/2000/svg"}):
        elem.tag = "switch"
        sort_switch_texts(elem)

    if save_result:
        if not output_file and output_dir:
            output_file = output_dir / svg_file_path.name

        # Write the modified SVG
        try:
            tree.write(str(output_file), encoding='utf-8', xml_declaration=True, pretty_print=True)
        except Exception as e:
            logger.error(f"Failed writing {output_file}: {e}")
            tree = None

    logger.info(f"Saved modified SVG to {output_file}")

    logger.info(f"Processed {stats['processed_switches']} switches")
    logger.info(f"Inserted {stats['inserted_translations']} translations")
    logger.info(f"Updated {stats['updated_translations']} translations")
    logger.info(f"Skipped {stats['skipped_translations']} existing translations")

    return tree, stats


def inject(inject_file, *args, **kwargs):
    """Inject translations into a single SVG file and optionally return stats.

    Parameters:
        inject_file (pathlib.Path | str): Path to the SVG file to modify.
        *args: Positional arguments forwarded to :func:`_inject`.
        **kwargs: Keyword arguments forwarded to :func:`_inject`. When
            ``return_stats`` is truthy, both the XML tree and statistics dict are
            returned; otherwise only the tree is returned.

    Returns:
        lxml.etree._ElementTree | tuple[lxml.etree._ElementTree, dict]: The
        modified SVG tree, optionally paired with processing statistics when
        ``return_stats`` is requested.
    """

    tree, stats = _inject(inject_file, *args, **kwargs)

    # if tree is None: logger.error(f"Failed to inject translations into {inject_file}")

    if kwargs.get("return_stats"):
        return tree, stats

    return tree
