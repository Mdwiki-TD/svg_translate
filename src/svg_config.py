"""

"""
import os
from pathlib import Path
# ---
from dotenv import load_dotenv
# ---
HOME = os.getenv("HOME")
# ---
env_file_path = f"{HOME}/confs/.env" if (HOME and os.path.exists(f"{HOME}/confs/.env")) else ".env"
# ---
load_dotenv(env_file_path)
# ---
home_dir = HOME if HOME else os.path.expanduser("~")
# ---
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
SVG_DATA_PATH = os.getenv("SVG_DATA_PATH", f"{home_dir}/svg_data")
LOG_DIR_PATH = os.getenv("LOG_PATH", f"{home_dir}/logs")
DISABLE_UPLOADS = os.getenv("DISABLE_UPLOADS", "1")
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
