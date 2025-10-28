"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from typing import Optional, Dict


@dataclass(frozen=True)
class DbConfig:
    db_name: str
    db_host: str
    db_user: str | None
    db_password: str | None
    db_connect_file: str | None


@dataclass(frozen=True)
class Paths:
    svg_data: str
    log_dir: str


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
    upload_host: str


@dataclass(frozen=True)
class Settings:
    db_data: Dict
    database_data: DbConfig
    STATE_SESSION_KEY: str
    REQUEST_TOKEN_SESSION_KEY: str
    secret_key: str
    use_mw_oauth: bool
    oauth_encryption_key: Optional[str]
    cookie: CookieConfig
    oauth: Optional[OAuthConfig]
    paths: Paths
    disable_uploads: str


def _load_db_data_new() -> DbConfig:
    db_connect_file = os.getenv("DB_CONNECT_FILE", os.path.join(os.path.expanduser('~'), 'replica.my.cnf'))

    return DbConfig(
        db_name=os.getenv("DB_NAME", ""),
        db_host=os.getenv("DB_HOST", ""),
        db_user=os.getenv("DB_USER", None),
        db_password=os.getenv("DB_PASSWORD", None),
        db_connect_file=db_connect_file if os.path.exists(db_connect_file) else None
    )


def _load_db_data() -> dict[str, str]:

    db_connect_file = os.getenv("DB_CONNECT_FILE", os.path.join(os.path.expanduser('~'), 'replica.my.cnf'))

    db_data = {
        "host": os.getenv("DB_HOST", ""),
        "dbname": os.getenv("DB_NAME", ""),
        "user": os.getenv("DB_USER", ""),
        "password": os.getenv("DB_PASSWORD", ""),
    }

    if os.path.exists(db_connect_file):
        db_data["db_connect_file"] = db_connect_file

    return db_data


def _get_paths() -> Paths:
    result = Paths(
        svg_data=os.getenv("SVG_DATA_PATH", f"{os.path.expanduser('~')}/www/svg_data"),
        log_dir=os.getenv("LOG_PATH", f"{os.path.expanduser("~")}/logs")
    )

    svg_data_dir = Path(result.svg_data)
    svg_data_dir.mkdir(parents=True, exist_ok=True)

    return result


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
            "USER_AGENT", "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)"
        ),
        upload_host=os.getenv("UPLOAD_END_POINT", "commons.wikimedia.org"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:

    secret_key = os.getenv("FLASK_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("FLASK_SECRET_KEY environment variable is required")

    session_cookie_secure = _env_bool("SESSION_COOKIE_SECURE", default=True)
    session_cookie_httponly = _env_bool("SESSION_COOKIE_HTTPONLY", default=True)
    session_cookie_samesite = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    STATE_SESSION_KEY = os.getenv("STATE_SESSION_KEY", "oauth_state_nonce")
    REQUEST_TOKEN_SESSION_KEY = os.getenv("REQUEST_TOKEN_SESSION_KEY", "state")

    use_mw_oauth = _env_bool("USE_MW_OAUTH", default=True)
    oauth_config = _load_oauth_config()

    oauth_encryption_key = os.getenv("OAUTH_ENCRYPTION_KEY")
    if use_mw_oauth and not oauth_encryption_key:
        raise RuntimeError(
            "OAUTH_ENCRYPTION_KEY environment variable is required when USE_MW_OAUTH is enabled"
        )

    cookie = CookieConfig(
        name=os.getenv("AUTH_COOKIE_NAME", "uid_enc"),
        max_age=_env_int("AUTH_COOKIE_MAX_AGE", 30 * 24 * 3600),
        secure=session_cookie_secure,
        httponly=session_cookie_httponly,
        samesite=session_cookie_samesite,
    )

    if use_mw_oauth and oauth_config is None:
        raise RuntimeError(
            "MediaWiki OAuth configuration is incomplete. Set OAUTH_MWURI, OAUTH_CONSUMER_KEY, and OAUTH_CONSUMER_SECRET."
        )

    return Settings(
        paths=_get_paths(),
        database_data=_load_db_data_new(),
        db_data=_load_db_data(),
        STATE_SESSION_KEY=STATE_SESSION_KEY,
        REQUEST_TOKEN_SESSION_KEY=REQUEST_TOKEN_SESSION_KEY,
        secret_key=secret_key,
        use_mw_oauth=use_mw_oauth,
        oauth_encryption_key=oauth_encryption_key,
        cookie=cookie,
        oauth=oauth_config,
        disable_uploads=os.getenv("DISABLE_UPLOADS", "")
    )


settings = get_settings()
