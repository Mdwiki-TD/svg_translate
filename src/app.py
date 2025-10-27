"""WSGI entry point for SVG Translate."""

from __future__ import annotations
import sys
from app import svg_config  # load_dotenv()
from log import config_console_logger
from app import create_app

config_console_logger()

app = create_app()

if __name__ == "__main__":
    debug = "debug" in sys.argv
    app.run(debug=debug)
