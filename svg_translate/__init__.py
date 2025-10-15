

from .start_bot import start_on_template_title

from .svgpy import svg_extract_and_injects, svg_extract_and_inject, extract, inject, normalize_text, generate_unique_id
from .commons import upload_file, get_wikitext, download_commons_svgs, get_files


__all__ = [
    "start_on_template_title",
    "svg_extract_and_inject",
    "svg_extract_and_injects",
    "extract",
    "inject",
    "upload_file",
    "download_commons_svgs",
    "get_wikitext",
    "get_files",
    "normalize_text",
    "generate_unique_id",
]
