"""
Central configuration for the SVG Translate web application.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
# ---
_HOME = os.getenv("HOME")
# ---
_env_file_path = f"{_HOME}/confs/.env" if (_HOME and os.path.exists(f"{_HOME}/confs/.env")) else ".env"
# ---
load_dotenv(_env_file_path)
# ---
_home_dir = _HOME if _HOME else os.path.expanduser("~")
# ---
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
SVG_DATA_PATH = os.getenv("SVG_DATA_PATH", f"{_home_dir}/svg_data")
LOG_DIR_PATH = os.getenv("LOG_PATH", f"{_home_dir}/logs")
DISABLE_UPLOADS = os.getenv("DISABLE_UPLOADS", "")
# ---
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_HOST = os.getenv("DB_HOST", "")
# ---
COMMONS_USER = os.getenv("COMMONS_USER", "")
COMMONS_PASSWORD = os.getenv("COMMONS_PASSWORD", "")
# ---

svg_data_dir = Path(SVG_DATA_PATH)
svg_data_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# OAuth configuration
# ---------------------------------------------------------------------------

OAUTH_MWURI = os.getenv("OAUTH_MWURI", "")
OAUTH_CONSUMER_KEY = os.getenv("OAUTH_CONSUMER_KEY", "")
OAUTH_CONSUMER_SECRET = os.getenv("OAUTH_CONSUMER_SECRET", "")
OAUTH_ENCRYPTION_KEY = os.getenv("OAUTH_ENCRYPTION_KEY", "")

AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "svg_translate_user")
AUTH_COOKIE_MAX_AGE = int(os.getenv("AUTH_COOKIE_MAX_AGE", 0)) or 30 * 24 * 60 * 60
REQUEST_TOKEN_SESSION_KEY = os.getenv("REQUEST_TOKEN_SESSION_KEY", "oauth_request_token")
STATE_SESSION_KEY = os.getenv("STATE_SESSION_KEY", "oauth_state")
COOKIE_SALT = os.getenv("COOKIE_SALT", "svg-translate-user")
STATE_SALT = os.getenv("STATE_SALT", "svg-translate-state")

USER_AGENT = os.getenv("USER_AGENT", "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)")

db_data = {
    "host": DB_HOST,
    "dbname": DB_NAME,

    "user": DB_USER,
    "password": DB_PASSWORD,
}

db_connect_file = os.getenv("DB_CONNECT_FILE", os.path.join(os.path.expanduser('~'), 'replica.my.cnf'))

if os.path.exists(db_connect_file):
    db_data["db_connect_file"] = db_connect_file

user_data = {
    "username": COMMONS_USER,
    "password": COMMONS_PASSWORD
}

__all__ = [
    "USER_AGENT",
    "SECRET_KEY",
    "SVG_DATA_PATH",
    "LOG_DIR_PATH",
    "DISABLE_UPLOADS",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_HOST",
    "COMMONS_USER",
    "COMMONS_PASSWORD",
    "svg_data_dir",
    "db_data",
    "db_connect_file",
    "user_data",
    "OAUTH_MWURI",
    "OAUTH_CONSUMER_KEY",
    "OAUTH_CONSUMER_SECRET",
    "OAUTH_ENCRYPTION_KEY",
    "AUTH_COOKIE_NAME",
    "AUTH_COOKIE_MAX_AGE",
    "REQUEST_TOKEN_SESSION_KEY",
    "STATE_SESSION_KEY",
    "COOKIE_SALT",
    "STATE_SALT"
]
