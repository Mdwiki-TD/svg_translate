#!/usr/bin/env python3
from svgtranslate import extract
import json

result = extract('test_multiple_tspans.svg')
with open('../data/test_multiple_tspans.svg.json', 'w') as f:
    json.dump(result, f, indent=2)
