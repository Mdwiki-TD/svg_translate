

from .svgpy import svg_extract_and_injects, svg_extract_and_inject, extract, inject, normalize_text, generate_unique_id
from .commons import get_wikitext, get_files

from .injects_files import start_injects

__all__ = [
    "start_injects",
    "svg_extract_and_inject",
    "svg_extract_and_injects",
    "extract",
    "inject",
    "get_wikitext",
    "get_files",
    "normalize_text",
    "generate_unique_id",
]
