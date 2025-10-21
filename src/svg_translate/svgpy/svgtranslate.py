#!/usr/bin/env python3
"""
SVG Translation Tool

This tool extracts multilingual text pairs from SVG files and applies translations
to other SVG files by inserting missing <text systemLanguage="XX"> blocks.
"""

import json
from pathlib import Path
import logging

from .bots.extract_bot import extract
from .bots.inject_bot import inject

logger = logging.getLogger(__name__)

def svg_extract_and_inject(extract_file, inject_file, output_file=None, data_output_file=None, overwrite=None, save_result=False):
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
        # json_output_dir = Path.cwd() / "data"
        json_output_dir = Path(__file__).parent / "data"
        json_output_dir.mkdir(parents=True, exist_ok=True)

        data_output_file = json_output_dir / f'{extract_file.name}.json'

    # Save translations to JSON
    with open(data_output_file, 'w', encoding='utf-8') as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved translations to {data_output_file}")

    if not output_file:
        # output_dir = Path.cwd() / "translated"
        output_dir = Path(__file__).parent / "translated"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / inject_file.name

    logger.debug("______________________\n"*5)

    tree, stats = inject(inject_file, mapping_files=[data_output_file], output_file=output_file, overwrite=overwrite, save_result=save_result, return_stats=True)

    if tree is None:
        logger.error(f"Failed to inject translations into {inject_file}")

    return tree


def svg_extract_and_injects(translations, inject_file, output_dir=None, save_result=False, **kwargs):

    inject_file = Path(str(inject_file))

    if not output_dir and save_result:
        output_dir = Path(__file__).parent / "translated"
        output_dir.mkdir(parents=True, exist_ok=True)

    return inject(inject_file, output_dir=output_dir, all_mappings=translations, save_result=save_result, **kwargs)
