"""Svg viewer"""

import logging
from pathlib import Path
from lxml import etree

logger = logging.getLogger(__name__)


def file_langs(file_path: Path):
    languages = set()
    # ---
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(str(file_path), parser)
        root = tree.getroot()
        # Second pass on text elements for extra checks and switch creation
        # texts = root.findall(".//{%s}text" % svg_ns)
        text_elements = root.xpath('.//svg:text', namespaces={'svg': 'http://www.w3.org/2000/svg'})
        for text in text_elements:
            # normalize systemLanguage if present
            if text.get("systemLanguage"):
                languages.add(text.get("systemLanguage"))
    except (etree.XMLSyntaxError, OSError):
        logger.exception(f"Error parsing SVG file: {file_path}")
    # ---
    return list(languages)


def analyze_file(file_path: Path):
    # TODO: compare the two SVG files and return comparison results
    result = {
        "languages" : file_langs(file_path),
    }

    return result


def compare_svg_files(file_path: Path, translated_path: Path):
    # ---
    file_result = analyze_file(file_path)
    translated_result = analyze_file(translated_path)

    return [file_result, translated_result]
