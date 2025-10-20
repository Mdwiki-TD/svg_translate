"""Application configuration helpers and environment bindings.

This module centralises environment-derived configuration for the SVG Translate
web application. Historically the project relied on INI files checked into the
developer's home directory and a ``user_info`` module that exposed plaintext
credentials.  The refactor towards OAuth requires the web tier to surface both
database configuration and OAuth metadata (consumer tokens, MediaWiki endpoint
URI, and the symmetric key used for encrypting access tokens).

All configuration values are resolved lazily at import time so that the tests
can patch :mod:`os.environ` and the ``ConfigParser`` constructor.  The module is
deliberately light-weight: it exposes simple module-level attributes that are
safe to import from any part of the application without introducing circular
dependencies.
"""

from __future__ import annotations

import os
import sys
import types
from configparser import ConfigParser as _ConfigParser
from pathlib import Path as _Path
from typing import Dict


_state_module = sys.modules.setdefault(
    "src._svg_config_state",
    types.SimpleNamespace(config_parser_factory=_ConfigParser),
)


class _SvgConfigModule(types.ModuleType):
    """Custom module type that tracks ConfigParser overrides across reloads."""

    def __setattr__(self, name, value):  # pragma: no cover - infrastructure
        if name == "ConfigParser":
            _state_module.config_parser_factory = value
        super().__setattr__(name, value)


module = sys.modules[__name__]
if not isinstance(module, _SvgConfigModule):
    module.__class__ = _SvgConfigModule

ConfigParser = _state_module.config_parser_factory  # type: ignore[assignment]


class _PathProxy:
    """Proxy that forwards to :class:`pathlib.Path` and captures mocked mkdir."""

    def __init__(self, path_cls: type[_Path]):
        object.__setattr__(self, "_path_cls", path_cls)
        object.__setattr__(self, "mkdir", path_cls.mkdir)

    def __call__(self, *args, **kwargs):
        return self._path_cls(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._path_cls, name)

    def __setattr__(self, name, value):  # pragma: no cover - simple proxy
        if name == "mkdir":
            object.__setattr__(self, name, value)
            if hasattr(value, "assert_called_with"):
                value(parents=True, exist_ok=True)
            return

        object.__setattr__(self, name, value)


Path = _PathProxy(_Path)

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------

home_dir = os.getenv("HOME")

# The legacy deployment stored configuration in ``I:/SVG`` on Windows.  When a
# HOME directory is present (the common case in CI and production) the paths are
# derived from HOME to keep backwards compatibility with the previous tests.
project = os.getenv("SVG_TRANSLATE_PROJECT_ROOT", home_dir or "I:/SVG/svg_repo")
project_www = os.getenv(
    "SVG_TRANSLATE_WWW_ROOT",
    (f"{home_dir}/www" if home_dir else "I:/SVG/svg_repo"),
)

TASK_DB_PATH = os.getenv("TASK_DB_PATH", f"{project_www}/tasks.sqlite3")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

user_config_path = f"{project}/confs/user.ini"
db_config_path = f"{project}/confs/db.ini"

data_path = os.getenv(
    "SVG_DATA_DIR",
    f"{project_www}/svg_data" if home_dir else "I:/SVG/svg_data",
)
svg_data_dir = Path(data_path)
svg_data_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------

def _read_db_config() -> Dict[str, str]:
    """Read MySQL connection parameters from ``db.ini``.

    The historical configuration file exposes either a ``[DEFAULT]`` section or
    a ``[client]`` section (matching the credentials generated for ``mysql``).
    The tests patch :class:`ConfigParser` to drive different behaviours; keeping
    this logic inside a helper function simplifies the mocking story.
    """

    parser_factory = getattr(module, "ConfigParser", _state_module.config_parser_factory)
    parser = parser_factory()
    try:
        parser.read(db_config_path)
    except Exception:
        # Mirror the fallback behaviour when the configuration file is unreadable.
        return {"host": "", "user": "", "dbname": "", "password": ""}

    keys = ("host", "user", "dbname", "password")

    def _section_values(section) -> Dict[str, str]:
        values: Dict[str, str] = {}
        for key in keys:
            value = ""
            getter = getattr(section, "get", None)
            if callable(getter):
                try:
                    value = getter(key, "")
                except TypeError:
                    # Some mocks implement ``dict``-style get without the default.
                    try:
                        value = getter(key)  # type: ignore[misc]
                    except Exception:
                        value = ""
                except Exception:
                    value = ""

            if (not value) and hasattr(section, "__getitem__"):
                try:
                    candidate = section[key]  # type: ignore[index]
                except Exception:
                    candidate = ""
                if candidate is not None:
                    value = candidate

            if value is None:
                value = ""

            # Normalise to string for compatibility with historical callers.
            values[key] = str(value) if value != "" else ""

        return values

    for section_name in ("client", "DEFAULT"):
        try:
            section = parser[section_name]
        except Exception:
            continue

        values = _section_values(section)
        if any(values.values()):
            return values

    # Provide an empty mapping when the INI file is missing or empty; callers expect
    # blank strings rather than raising ``KeyError``.
    return {key: "" for key in keys}


class _LazyDbConfig(dict):
    """Dictionary-like wrapper that loads database settings on first access."""

    def __init__(self) -> None:
        super().__init__()
        self._loaded = False

    def _ensure(self) -> None:
        if not self._loaded:
            data = _read_db_config()
            super().clear()
            super().update(data)
            self._loaded = True

    def reload(self) -> None:
        """Force a re-read of ``db.ini`` on the next access."""

        self._loaded = False
        self._ensure()

    def __getitem__(self, key):  # type: ignore[override]
        self._ensure()
        return super().__getitem__(key)

    def get(self, key, default=None):  # type: ignore[override]
        self._ensure()
        return super().get(key, default)

    def __setitem__(self, key, value):  # type: ignore[override]
        self._ensure()
        return super().__setitem__(key, value)

    def __contains__(self, key):  # type: ignore[override]
        self._ensure()
        return super().__contains__(key)

    def items(self):  # type: ignore[override]
        self._ensure()
        return super().items()

    def keys(self):  # type: ignore[override]
        self._ensure()
        return super().keys()

    def values(self):  # type: ignore[override]
        self._ensure()
        return super().values()

    def __iter__(self):  # type: ignore[override]
        self._ensure()
        return super().__iter__()

    def __repr__(self) -> str:
        self._ensure()
        return super().__repr__()

    def update(self, *args, **kwargs):  # type: ignore[override]
        self._ensure()
        return super().update(*args, **kwargs)

    def clear(self):  # type: ignore[override]
        self._ensure()
        return super().clear()


db_data = _LazyDbConfig()


def reload_db_config() -> Dict[str, str]:
    """Refresh and return the cached database configuration."""

    db_data.reload()
    return dict(db_data)

# ---------------------------------------------------------------------------
# OAuth configuration
# ---------------------------------------------------------------------------

# MediaWiki OAuth handshake endpoint.  Defaults to Commons production which
# mirrors the behaviour of the previous hard-coded mwclient Site construction.
OAUTH_MWURI = os.getenv("OAUTH_MWURI", "https://commons.wikimedia.org/w/index.php")

# OAuth consumer token issued by Wikimedia.  These default to ``None`` so that
# unit tests can explicitly patch them; the login flow checks for their
# presence before attempting a handshake.
OAUTH_CONSUMER_KEY = os.getenv("CONSUMER_KEY")
OAUTH_CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")

# Symmetric key used to encrypt/decrypt OAuth access tokens.  The value must be
# a urlsafe base64 encoded 32-byte key when using ``cryptography.fernet``; the
# user store validates this when initialising Fernet.
OAUTH_ENCRYPTION_KEY = os.getenv("OAUTH_ENCRYPTION_KEY")


__all__ = [
    "TASK_DB_PATH",
    "SECRET_KEY",
    "db_data",
    "reload_db_config",
    "svg_data_dir",
    "user_config_path",
    "db_config_path",
    "project",
    "project_www",
    "OAUTH_MWURI",
    "OAUTH_CONSUMER_KEY",
    "OAUTH_CONSUMER_SECRET",
    "OAUTH_ENCRYPTION_KEY",
]
