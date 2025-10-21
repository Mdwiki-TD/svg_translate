"""WSGI entry point for SVG Translate."""

from __future__ import annotations

from .app import create_app

app = create_app()
