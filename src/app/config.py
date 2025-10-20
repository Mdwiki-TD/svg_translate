"""Configuration helpers for the SVG Translate Flask application."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
OAUTH_MWURI: Optional[str] = os.getenv("OAUTH_MWURI")
CONSUMER_KEY: Optional[str] = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET: Optional[str] = os.getenv("CONSUMER_SECRET")
FERNET_KEY: Optional[str] = os.getenv("FERNET_KEY")
USE_MW_OAUTH: bool = _env_bool("USE_MW_OAUTH", default=True)
SESSION_COOKIE_SECURE: bool = _env_bool("SESSION_COOKIE_SECURE", default=False)
SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_HTTPONLY: bool = _env_bool("SESSION_COOKIE_HTTPONLY", default=True)
OAUTH_USER_AGENT: str = os.getenv(
    "OAUTH_USER_AGENT", "SVGTranslate/1.0 (svgtranslate@example.org)"
)
OAUTH_API_HOST: Optional[str] = os.getenv("OAUTH_API_HOST", "commons.wikimedia.org")
OAUTH_API_PATH: str = os.getenv("OAUTH_API_PATH", "/w/")
UID_COOKIE_NAME: str = os.getenv("UID_COOKIE_NAME", "uid_enc")
UID_COOKIE_MAX_AGE: int = int(os.getenv("UID_COOKIE_MAX_AGE", str(7 * 24 * 3600)))
