

from .start_bot import start_on_template_title

from .svgpy import svg_extract_and_injects, svg_extract_and_inject, extract, inject, normalize_text, generate_unique_id
from .commons import upload_file, get_wikitext, download_commons_svgs, get_files

from .injects_files import start_injects
from .upload_files import start_upload
from .log import logger, config_logger

__all__ = [
    "start_injects",
    "start_upload",
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
    "logger",
    "config_logger",
]
