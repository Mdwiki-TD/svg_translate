"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Environment variable {name} must be an integer") from exc


@dataclass(frozen=True)
class CookieConfig:
    name: str
    max_age: int
    secure: bool
    httponly: bool
    samesite: str


@dataclass(frozen=True)
class OAuthConfig:
    mw_uri: str
    consumer_key: str
    consumer_secret: str
    user_agent: str
    api_host: str
    api_path: str


@dataclass(frozen=True)
class Settings:
    secret_key: str
    session_cookie_secure: bool
    session_cookie_httponly: bool
    session_cookie_samesite: str
    use_mw_oauth: bool
    oauth_encryption_key: Optional[str]
    cookie: CookieConfig
    oauth: Optional[OAuthConfig]


def _load_oauth_config() -> Optional[OAuthConfig]:
    mw_uri = os.getenv("OAUTH_MWURI")
    consumer_key = os.getenv("OAUTH_CONSUMER_KEY")
    consumer_secret = os.getenv("OAUTH_CONSUMER_SECRET")
    if not (mw_uri and consumer_key and consumer_secret):
        return None

    return OAuthConfig(
        mw_uri=mw_uri,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        user_agent=os.getenv(
            "USER_AGENT", "SVGTranslate/1.0 (svgtranslate@example.org)"
        ),
        api_host=os.getenv("OAUTH_API_HOST", "commons.m.wikimedia.org"),
        api_path=os.getenv("OAUTH_API_PATH", "/w/"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    secret_key = os.getenv("FLASK_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("FLASK_SECRET_KEY environment variable is required")

    session_cookie_secure = _env_bool("SESSION_COOKIE_SECURE", default=True)
    session_cookie_httponly = _env_bool("SESSION_COOKIE_HTTPONLY", default=True)
    session_cookie_samesite = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

    use_mw_oauth = _env_bool("USE_MW_OAUTH", default=True)
    oauth_config = _load_oauth_config()

    oauth_encryption_key = os.getenv("OAUTH_ENCRYPTION_KEY")
    if use_mw_oauth and not oauth_encryption_key:
        raise RuntimeError(
            "OAUTH_ENCRYPTION_KEY environment variable is required when USE_MW_OAUTH is enabled"
        )

    cookie = CookieConfig(
        name=os.getenv("UID_COOKIE_NAME", "uid_enc"),
        max_age=_env_int("UID_COOKIE_MAX_AGE", 30 * 24 * 3600),
        secure=session_cookie_secure,
        httponly=session_cookie_httponly,
        samesite=session_cookie_samesite,
    )

    if use_mw_oauth and oauth_config is None:
        raise RuntimeError(
            "MediaWiki OAuth configuration is incomplete. Set OAUTH_MWURI, OAUTH_CONSUMER_KEY, and OAUTH_CONSUMER_SECRET."
        )

    return Settings(
        secret_key=secret_key,
        session_cookie_secure=session_cookie_secure,
        session_cookie_httponly=session_cookie_httponly,
        session_cookie_samesite=session_cookie_samesite,
        use_mw_oauth=use_mw_oauth,
        oauth_encryption_key=oauth_encryption_key,
        cookie=cookie,
        oauth=oauth_config,
    )


settings = get_settings()
