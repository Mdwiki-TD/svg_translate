"""WSGI entry point for SVG Translate."""

from __future__ import annotations
import sys
from app import create_app

import svg_config  # load_dotenv()

app = create_app()

if __name__ == "__main__":
    debug = "debug" in sys.argv
    app.run(debug=debug)
