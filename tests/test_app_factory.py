"""Regression tests for the Flask application factory."""

from __future__ import annotations

from importlib import reload

from src.app.db import svg_db


def test_create_app_does_not_touch_mysql_when_unconfigured(monkeypatch):
    """Ensure the app factory can run without MySQL credentials."""

    # Reset any cached connection and explicitly mark the configuration as empty.
    monkeypatch.setattr(svg_db, "_db", None)
    monkeypatch.setitem(svg_db.settings.db_data, "host", "")
    monkeypatch.setitem(svg_db.settings.db_data, "db_connect_file", "")

    class _SentinelDatabase:
        def __init__(self, *_args, **_kwargs):  # pragma: no cover - defensive guard
            raise AssertionError("Database should not be instantiated during app creation")

    monkeypatch.setattr(svg_db, "Database", _SentinelDatabase)

    # Reload to ensure the latest configuration is used if the module was cached.
    import src.app as app_module

    reload(app_module)

    app = app_module.create_app()

    assert app is not None
