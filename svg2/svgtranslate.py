#!/usr/bin/env python3
"""
SVG Translation Tool

Extract multilingual text pairs from an SVG file and save them as `original.svg.json`.
Then apply saved translations to other SVG files by inserting missing `<text systemLanguage="XX">` blocks.
"""
import io
import json
import logging
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from copy import deepcopy
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def normalize_text(text):
    """
    Normalize text by stripping leading/trailing whitespace and collapsing internal whitespace.
    """
    if not text:
        return ""
    # Replace multiple internal whitespace with single space and strip
    return ' '.join(text.split())


def extract_text_from_element(element):
    """
    Extract text from an SVG text element, preferring tspan content if present.
    """
    # Check for direct text content first
    if element.text:
        text_content = element.text
    else:
        text_content = ""

    # Look for tspan elements
    tspan_texts = []
    for child in element:
        if child.tag.endswith('tspan'):
            # Extract text from tspan - could be direct text or nested
            tspan_text = extract_text_from_tspan(child)
            tspan_texts.append(tspan_text)

    # Combine direct text and tspan text
    all_texts = [text_content] + tspan_texts
    combined_text = ''.join(all_texts)

    return normalize_text(combined_text)


def extract_text_from_tspan(tspan_element):
    """
    Extract text from an SVG tspan element, handling nested content.
    """
    text_parts = []

    # Add direct text content of tspan
    if tspan_element.text:
        text_parts.append(tspan_element.text)

    # Process nested elements if any
    for child in tspan_element:
        if child.text:
            text_parts.append(child.text)
        if child.tail:
            text_parts.append(child.tail)

    return ''.join(text_parts)


def get_default_text_element(switch_element):
    """
    Find the default text element (without systemLanguage attribute) in a switch element.
    """
    for child in switch_element:
        if child.tag.endswith('text') and 'systemLanguage' not in child.attrib:
            return child
    return None


def get_system_language_elements(switch_element):
    """
    Get all text elements with systemLanguage attribute in a switch element.
    """
    elements = []
    for child in switch_element:
        if child.tag.endswith('text') and 'systemLanguage' in child.attrib:
            elements.append(child)
    return elements


def generate_unique_id(base_id, existing_ids, suffix=""):
    """
    Generate a unique ID by appending a suffix and numeric counter if needed.
    """
    if not base_id:
        base_id = "text"

    candidate_id = f"{base_id}{suffix}"
    counter = 1

    while candidate_id in existing_ids:
        candidate_id = f"{base_id}{suffix}{counter}"
        counter += 1

    return candidate_id


def extract_translations(svg_path):
    """
    Extract multilingual text pairs from an SVG file and save to JSON.
    """
    # Parse SVG as XML
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Find all switch elements regardless of namespace
    def find_elements_by_tag(element, tag_name):
        """Find all elements with a specific tag name, ignoring namespace."""
        elements = []
        # Check if tag ends with the target tag_name regardless of namespace
        if element.tag.split('}')[-1] == tag_name:
            elements.append(element)
        for child in element:
            elements.extend(find_elements_by_tag(child, tag_name))
        return elements

    switch_elements = find_elements_by_tag(root, 'switch')

    data = {}
    switches_processed = 0
    languages_extracted = set()

    for switch in switch_elements:
        # Find default (no systemLanguage) text element
        default_element = get_default_text_element(switch)

        if default_element is None:
            logger.warning(f"Switch element without default text found in {svg_path}")
            continue

        # Extract English string from default element
        english_string = extract_text_from_element(default_element)

        if not english_string:
            logger.warning(f"Empty default text found in switch in {svg_path}")
            continue

        # Initialize translations dict for this English string
        if english_string not in data:
            data[english_string] = {}

        # Get all systemLanguage elements
        lang_elements = get_system_language_elements(switch)

        for lang_element in lang_elements:
            lang_code = lang_element.attrib.get('systemLanguage', '')
            if lang_code:
                translated_text = extract_text_from_element(lang_element)
                if translated_text:
                    data[english_string][lang_code] = translated_text
                    languages_extracted.add(lang_code)

        switches_processed += 1

    # Save data to JSON file
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f'{svg_path.name}.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Extracted translations from {switches_processed} switches with {len(languages_extracted)} languages to {output_file}")
    logger.info(f"Languages found: {', '.join(sorted(languages_extracted))}")

    return data


def validate_xml_well_formed(file_path):
    """
    Validate that an XML file is well-formed.
    """
    try:
        ET.parse(file_path)
        return True
    except ET.ParseError:
        return False


def inject_translations(svg_path, mapping_data, dry_run=False, overwrite=False):
    """
    Inject translations from JSON mapping into an SVG file.
    """
    # Parse SVG
    tree = ET.parse(svg_path)
    root = tree.getroot()

    output_dir = Path(__file__).parent / 'translated'
    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / svg_path.name

    # Find all switch elements regardless of namespace
    def find_elements_by_tag(element, tag_name):
        """Find all elements with a specific tag name, ignoring namespace."""
        elements = []
        # Check if tag ends with the target tag_name regardless of namespace
        if element.tag.split('}')[-1] == tag_name:
            elements.append(element)
        for child in element:
            elements.extend(find_elements_by_tag(child, tag_name))
        return elements

    switch_elements = find_elements_by_tag(root, 'switch')

    # Create a set of existing IDs to ensure uniqueness
    existing_ids = set()

    def collect_ids(element):
        if 'id' in element.attrib:
            existing_ids.add(element.attrib['id'])
        for child in element:
            collect_ids(child)

    collect_ids(root)

    changes_made = 0

    for switch in switch_elements:
        # Find default text element
        default_element = get_default_text_element(switch)

        if default_element is None:
            continue

        # Extract English string from default element
        english_string = extract_text_from_element(default_element)

        if not english_string or english_string not in mapping_data:
            continue

        # Get translations for this English string
        translations = mapping_data[english_string]

        for lang_code, translated_text in translations.items():
            # Check if a text element with this language already exists
            lang_element_exists = False
            existing_lang_element = None
            for child in switch:
                if (child.tag.split('}')[-1] == 'text' and
                        child.attrib.get('systemLanguage', '') == lang_code):
                    lang_element_exists = True
                    existing_lang_element = child
                    break

            if lang_element_exists and overwrite:
                # Update existing translation if different
                existing_text = extract_text_from_element(existing_lang_element)
                if existing_text != translated_text:
                    # Update the text content - handle both direct text and tspan
                    update_element_text(existing_lang_element, translated_text)
                    logger.info(f"Updated {lang_code} translation for '{english_string}' in {svg_path}")
                    changes_made += 1
            elif not lang_element_exists:
                # Create new text element with systemLanguage
                new_text_element = create_language_text_element(default_element, lang_code, translated_text, existing_ids)

                # Add the new element to the switch
                switch.append(new_text_element)

                logger.info(f"Inserted {lang_code} translation for '{english_string}' in {svg_path}")
                changes_made += 1

    # Validate the XML before writing the main file
    # Write modified SVG using atomic write
    # Create temp file in the same directory as the target to avoid cross-drive issues

    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.svg', dir=output_dir) as tmp_file:
        # Write to a bytes buffer first
        bytes_io = io.BytesIO()
        tree.write(bytes_io, encoding='utf-8', xml_declaration=True)
        tmp_file.write(bytes_io.getvalue())
        tmp_path = tmp_file.name

    # Validate the temporary file before replacing the original
    if not validate_xml_well_formed(tmp_path):
        logger.error(f"Generated XML is not well-formed for {svg_path}. Aborting write.")
        Path(tmp_path).unlink()  # Remove the invalid temp file
        raise ET.ParseError("Generated XML is not well-formed")

    # Replace original with temp file using os.replace for cross-platform compatibility

    shutil.move(tmp_path, svg_path)

    return changes_made


def update_element_text(element, new_text):
    """
    Update the text content of an SVG element, handling both direct text and tspan elements.
    """
    # Look for tspan elements first
    tspan_updated = False
    for child in element:
        if child.tag.split('}')[-1] == 'tspan':
            child.text = new_text
            tspan_updated = True
            break

    # If no tspan found, update the element's direct text
    if not tspan_updated:
        element.text = new_text


def create_language_text_element(default_element, lang_code, translated_text, existing_ids):
    """
    Create a new text element with systemLanguage attribute based on a default element.
    """
    # Create a deep copy of the default element
    new_text_element = deepcopy(default_element)

    # Set the systemLanguage attribute
    new_text_element.attrib['systemLanguage'] = lang_code

    # Generate and set unique ID if the original had one
    if 'id' in new_text_element.attrib:
        old_id = new_text_element.attrib['id']
        new_id = generate_unique_id(old_id, existing_ids, f"-{lang_code}")
        new_text_element.attrib['id'] = new_id
        existing_ids.add(new_id)

    # Update the text content
    update_element_text(new_text_element, translated_text)

    # Handle tspan IDs if they exist
    for child in new_text_element:
        if child.tag.split('}')[-1] == 'tspan' and 'id' in child.attrib:
            old_tspan_id = child.attrib['id']
            new_tspan_id = generate_unique_id(old_tspan_id, existing_ids, f"-{lang_code}")
            child.attrib['id'] = new_tspan_id
            existing_ids.add(new_tspan_id)

    return new_text_element


def main():
    Dir = Path(__file__).parent
    mapping_data = extract_translations(Dir / "arabic.svg")
    changes = inject_translations(Dir / "no_translations.svg", mapping_data)

    print("______________________\n"*5)

    mapping_data = extract_translations(Dir.parent / "big_example/file2.svg")
    changes = inject_translations(Dir.parent / "big_example/file1.svg", mapping_data)


if __name__ == '__main__':
    main()
