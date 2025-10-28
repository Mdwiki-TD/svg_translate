"""Svg viewer"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def analyze_file(file_path: Path):
    # TODO: compare the two SVG files and return comparison results
    result = {
        "number_of_langs" : 0,
        "number_of_texts": 0,
    }
    return result


def compare_svg_files(file_path: Path, translated_path: Path):
    file_result = analyze_file(file_path)
    translated_result = analyze_file(translated_path)

    return [file_result, translated_result]
