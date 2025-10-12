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


def main():
    """
    Main function that demonstrates the usage of extract and inject functions
    with various SVG files and their corresponding JSON data files.
    """
    # Set up logging
    setup_logging(False)

    Dir = Path(__file__).parent  # Get the directory path of the current script
    _data = extract(Dir / "files1/arabic.svg")  # Extract data from the first SVG file
    print("______________________\n"*5)  # Print separator line for visual clarity

    _result = inject(Dir / "files1/no_translations.svg", [Dir / "data/arabic.svg.json"])

    print("______________________\n"*5)

    _data2 = extract(Dir.parent / "big_example/file2.svg")
    print("______________________\n"*5)

    _result2 = inject(Dir.parent / "big_example/file1.svg", [Dir / "data/file2.svg.json"])

    _data = extract(Dir / "files2/from.svg")
    print("______________________\n"*5)

    _result = inject(Dir / "files2/to.svg", [Dir / "data/from.svg.json"])


def test():
    # Set up logging
    setup_logging(False)
    Dir = Path(__file__).parent

    _data = extract(Dir / "files2/from2.svg")

    print("______________________\n"*5)

    _result = inject(Dir / "files2/to2_raw.svg", [Dir / "data/from2.svg.json"])


if __name__ == '__main__':
    test()
