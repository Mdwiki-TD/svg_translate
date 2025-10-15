#!/usr/bin/env python3

from svgpy.svgtranslate import extract
import json

from pathlib import Path
tests_files_dir = Path(__file__).parent.parent / "tests_files"

result = extract(tests_files_dir / 'test_multiple_tspans.svg')

with open(tests_files_dir / 'test_multiple_tspans.svg.json', 'w') as f:
    json.dump(result, f, indent=2)
