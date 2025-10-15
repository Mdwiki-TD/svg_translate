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

from .bots.extract_bot import extract
from .bots.inject_bot import inject

logger = logging.getLogger(__name__)


def config_logger():

    logging.basicConfig(
        level=logging.DEBUG if "DEBUG" in sys.argv else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def svg_extract_and_inject(extract_file, inject_file, output_file=None, data_output_file=None, overwrite=None):
    """
    Extract translations from one SVG file and inject them into another.

    Args:
        extract_file: Path to SVG file to extract translations from
        inject_file: Path to SVG file to inject translations into
        output_file: Optional output path for modified SVG (defaults to translated/<inject_file>)
        data_output_file: Optional output path for JSON data (defaults to data/<extract_file>.json)

    Returns:
        Dictionary with injection statistics, or None if extraction or injection fails
    """

    extract_file = Path(str(extract_file))
    inject_file = Path(str(inject_file))

    translations = extract(extract_file, case_insensitive=True)
    if not translations:
        logger.error(f"Failed to extract translations from {extract_file}")
        return None

    if not data_output_file:
        json_output_dir = Path(__file__).parent / "data"
        json_output_dir.mkdir(parents=True, exist_ok=True)

        data_output_file = json_output_dir / f'{extract_file.name}.json'

    # Save translations to JSON
    with open(data_output_file, 'w', encoding='utf-8') as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved translations to {data_output_file}")

    if not output_file:
        output_dir = Path(__file__).parent / "translated"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / inject_file.name

    print("______________________\n"*5)

    _result = inject(inject_file, mapping_files=[data_output_file], output_file=output_file, overwrite=overwrite)

    if _result is None:
        logger.error(f"Failed to inject translations into {inject_file}")

    return _result


def svg_extract_and_injects(translations, inject_file, output_dir=None, save_result=False, return_stats=False):

    inject_file = Path(str(inject_file))

    if not output_dir and save_result:
        output_dir = Path(__file__).parent / "translated"
        output_dir.mkdir(parents=True, exist_ok=True)

    return inject(inject_file, output_dir=output_dir, all_mappings=translations, save_result=save_result, return_stats=return_stats)
