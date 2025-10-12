#!/usr/bin/env python3
"""
SVG Translation Tool

This tool extracts multilingual text pairs from SVG files and applies translations
to other SVG files by inserting missing <text systemLanguage="XX"> blocks.
"""

import logging
from pathlib import Path

from bots.extract_bot import extract
from bots.inject_bot import inject


def setup_logging(verbose=False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def svg_extract_and_inject(extract_file, inject_file, output_file=None):
    """
    Main function that demonstrates the usage of extract and inject functions
    with various SVG files and their corresponding JSON data files.
    """
    Dir = Path(__file__).parent  # Get the directory path of the current script
    extract_file = Path(str(extract_file))

    if not output_file:
        # Save data to JSON file
        output_dir = Path(__file__).parent.parent / "translated"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / extract_file.name

    _data = extract(extract_file)

    print("______________________\n"*5)

    _result = inject(inject_file, [Dir / f"data/{extract_file.name}.json"], output_file=output_file)

    return _result


def test():
    # Set up logging
    setup_logging(False)

    Dir = Path(__file__).parent  # Get the directory path of the current script

    _result = svg_extract_and_inject(Dir / "tests/files1/arabic.svg", Dir / "tests/files1/no_translations.svg")

    print("______________________\n"*5)

    _2 = svg_extract_and_inject(Dir.parent / "big_example/file2.svg", Dir.parent / "big_example/file1.svg")
    print("______________________\n"*5)

    _3 = svg_extract_and_inject(Dir / "tests/files2/from.svg", Dir / "tests/files2/to.svg")

    print("______________________\n"*5)

    _data = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2_raw.svg")


if __name__ == '__main__':
    test()
