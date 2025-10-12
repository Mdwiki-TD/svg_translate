#!/usr/bin/env python3
"""
SVG Translation Tool

This tool extracts multilingual text pairs from SVG files and applies translations
to other SVG files by inserting missing <text systemLanguage="XX"> blocks.
"""

import json
import sys
import logging
from pathlib import Path

from bots.extract_bot import extract
from bots.inject_bot import inject

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG if "DEBUG" in sys.argv else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def svg_extract_and_inject(extract_file, inject_file, output_file=None, data_output_file=None):
    """
    Main function that demonstrates the usage of extract and inject functions
    with various SVG files and their corresponding JSON data files.
    """
    Dir = Path(__file__).parent  # Get the directory path of the current script
    extract_file = Path(str(extract_file))
    inject_file = Path(str(inject_file))

    if not output_file:
        output_dir = Path(__file__).parent / "translated"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / inject_file.name

    if not data_output_file:
        json_output_dir = Path(__file__).parent / "data"
        json_output_dir.mkdir(parents=True, exist_ok=True)

        data_output_file = json_output_dir / f'{extract_file.name}.json'

    translations = extract(extract_file, case_insensitive=True)

    if translations:
        # Save translations to JSON
        with open(data_output_file, 'w', encoding='utf-8') as f:
            json.dump(translations, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved translations to {data_output_file}")

    print("______________________\n"*5)

    _result = inject(inject_file, [data_output_file], output_file=output_file)

    return _result


def test():

    Dir = Path(__file__).parent  # Get the directory path of the current script

    _result = svg_extract_and_inject(Dir / "tests/files1/arabic.svg", Dir / "tests/files1/no_translations.svg")

    print("______________________\n"*5)

    _2 = svg_extract_and_inject(Dir.parent / "big_example/file2.svg", Dir.parent / "big_example/file1.svg")
    print("______________________\n"*5)

    # _3 = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2.svg")

    print("______________________\n"*5)

    _data = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2_raw.svg")


if __name__ == '__main__':
    test()
