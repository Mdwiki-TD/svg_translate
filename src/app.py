"""WSGI entry point for SVG Translate."""

from __future__ import annotations

import sys
from svg_config import _env_file_path  # noqa: F401 # Triggers environment configuration

from log import config_console_logger   # noqa: E402
from app import create_app              # noqa: E402

config_console_logger()

app = create_app()

if __name__ == "__main__":
    debug = "debug" in sys.argv
    app.run(debug=debug)
