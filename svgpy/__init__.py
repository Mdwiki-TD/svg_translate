

from .svgtranslate import svg_extract_and_injects
from .bots.extract_bot import extract
from .bots.inject_bot import inject

__all__ = [
    "svg_extract_and_injects",
    "extract",
    "inject",
]
