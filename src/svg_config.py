"""
Central configuration for the SVG Translate web application.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

_HOME = os.getenv("HOME")
_env_file_path = f"{_HOME}/confs/.env"

if _HOME is None or _HOME == "":
    _env_file_path = str(Path(__file__).parent / ".env")

load_dotenv(_env_file_path)

CopySvgTranslate_PATH = os.getenv("CopySvgTranslate_PATH", "")

try:
    import CopySvgTranslate  # type: ignore  # noqa: F401
except ImportError:
    if CopySvgTranslate_PATH and Path(CopySvgTranslate_PATH).is_dir():
        sys.path.insert(0, str(Path(CopySvgTranslate_PATH).parent))
