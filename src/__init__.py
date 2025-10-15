

from .start_bot import start_on_template_title
from .svgpy import svg_extract_and_injects, svg_extract_and_inject, extract, inject
from .commons.upload_bot import upload_file
from .commons.text_bot import get_wikitext
from .commons.download_bot import download_commons_svgs
from .commons.temps_bot import get_files
from .svgpy.bots.utils import normalize_text, generate_unique_id

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
