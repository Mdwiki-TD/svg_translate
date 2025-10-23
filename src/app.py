"""WSGI entry point for SVG Translate."""

from __future__ import annotations
import sys

import svg_config  # load_dotenv()
from log import config_console_logger

from app import create_app
config_console_logger()

w_app = create_app()

if __name__ == "__main__":
    debug = "debug" in sys.argv
    w_app.run(debug=debug)
