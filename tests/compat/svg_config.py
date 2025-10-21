"""Lightweight configuration for test/runtime compatibility."""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "TASK_DB_PATH",
    "SECRET_KEY",
    "svg_data_dir",
    "db_data",
    "user_config_path",
    "OAUTH_MWURI",
    "OAUTH_CONSUMER_KEY",
    "OAUTH_CONSUMER_SECRET",
    "OAUTH_ENCRYPTION_KEY",
]

_default_base = Path(os.getenv("HOME", Path.cwd()))
TASK_DB_PATH = os.getenv("TASK_DB_PATH", str(_default_base / "tasks.sqlite3"))
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
svg_data_dir = Path(os.getenv("SVG_DATA_DIR", _default_base / "svg_data"))
svg_data_dir.mkdir(parents=True, exist_ok=True)

db_data = {
    "host": os.getenv("DB_HOST", ""),
    "user": os.getenv("DB_USER", ""),
    "dbname": os.getenv("DB_NAME", ""),
    "password": os.getenv("DB_PASSWORD", ""),
}

user_config_path = os.getenv("USER_CONFIG_PATH", str(_default_base / "confs" / "user.ini"))

OAUTH_MWURI = os.getenv("OAUTH_MWURI", "https://commons.wikimedia.org/w/index.php")
OAUTH_CONSUMER_KEY = os.getenv("CONSUMER_KEY")
OAUTH_CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
OAUTH_ENCRYPTION_KEY = os.getenv("OAUTH_ENCRYPTION_KEY")
