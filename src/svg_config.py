"""Central configuration for the SVG Translate web application."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import os
from typing import Dict, Iterable, Iterator


from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Base paths and filesystem locations
# ---------------------------------------------------------------------------

_home = os.environ.get("HOME")
_project_default = _home if _home else "I:/SVG/svg_repo"
_www_default = f"{_home}/www" if _home else "I:/SVG/svg_repo"

project = os.environ.get("SVG_TRANSLATE_PROJECT_ROOT", _project_default)
project_www = os.environ.get("SVG_TRANSLATE_WWW_ROOT", _www_default)

user_config_path = os.environ.get("SVG_TRANSLATE_USER_CONFIG", f"{project}/confs/user.ini")
db_config_path = os.environ.get("SVG_TRANSLATE_DB_CONFIG", f"{project}/confs/db.ini")

TASK_DB_PATH = os.environ.get("TASK_DB_PATH", f"{project_www}/tasks.sqlite3")
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

_data_dir_default = os.environ.get(
    "SVG_DATA_DIR",
    f"{project_www}/svg_data" if _home else "I:/SVG/svg_data",
)
svg_data_dir = Path(_data_dir_default)
svg_data_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# OAuth configuration
# ---------------------------------------------------------------------------

OAUTH_MWURI = os.environ.get("OAUTH_MWURI", "")
OAUTH_CONSUMER_KEY = os.environ.get("CONSUMER_KEY", "")
OAUTH_CONSUMER_SECRET = os.environ.get("CONSUMER_SECRET", "")
OAUTH_ENCRYPTION_KEY = os.environ.get("OAUTH_ENCRYPTION_KEY", "")

# ---------------------------------------------------------------------------
# Database configuration helpers
# ---------------------------------------------------------------------------

ConfigParserFactory = ConfigParser


def _load_db_config() -> Dict[str, str]:
    """Read database configuration from the ``db.ini`` file."""

    parser = ConfigParserFactory()
    try:
        parser.read(db_config_path)
    except Exception:  # pragma: no cover - defensive fallback
        return {"host": "", "user": "", "dbname": "", "password": ""}

    keys = ("host", "user", "dbname", "password")

    def _section_values(section: object) -> Dict[str, str]:
        values: Dict[str, str] = {key: "" for key in keys}
        if not hasattr(section, "get") and not isinstance(section, dict):
            return values

        for key in keys:
            value = ""
            if hasattr(section, "get"):
                try:
                    value = section.get(key, "")  # type: ignore[call-arg]
                except Exception:
                    value = ""
            if (not value) and isinstance(section, dict):
                value = section.get(key, "")  # type: ignore[assignment]
            values[key] = str(value or "")
        return values

    for section_name in ("client", "DEFAULT"):
        try:
            section = parser[section_name]
        except Exception:
            continue
        values = _section_values(section)
        if any(values.values()):
            return values

    return {key: "" for key in keys}


class _LazyDbConfig(Dict[str, str]):
    """Lazy dictionary wrapper that reloads configuration on demand."""

    def __init__(self) -> None:
        super().__init__()
        self._loaded = False

    def _ensure(self) -> None:
        if not self._loaded:
            data = _load_db_config()
            super().clear()
            super().update(data)
            self._loaded = True

    def reload(self) -> None:
        self._loaded = False
        self._ensure()

    # Mapping interface -------------------------------------------------
    def __getitem__(self, key: str) -> str:  # type: ignore[override]
        self._ensure()
        return super().__getitem__(key)

    def get(self, key: str, default: str | None = None) -> str:  # type: ignore[override]
        self._ensure()
        return super().get(key, default or "")

    def items(self) -> Iterable[tuple[str, str]]:  # type: ignore[override]
        self._ensure()
        return super().items()

    def values(self) -> Iterable[str]:  # type: ignore[override]
        self._ensure()
        return super().values()

    def keys(self) -> Iterable[str]:  # type: ignore[override]
        self._ensure()
        return super().keys()

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        self._ensure()
        return super().__iter__()


db_data: Dict[str, str] = _LazyDbConfig()

__all__ = [
    "TASK_DB_PATH",
    "SECRET_KEY",
    "db_data",
    "svg_data_dir",
    "project",
    "project_www",
    "user_config_path",
    "db_config_path",
    "OAUTH_MWURI",
    "OAUTH_CONSUMER_KEY",
    "OAUTH_CONSUMER_SECRET",
    "OAUTH_ENCRYPTION_KEY",
]
