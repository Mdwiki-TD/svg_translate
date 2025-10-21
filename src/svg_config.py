"""

"""
import os
from configparser import ConfigParser
from pathlib import Path
# ---
from dotenv import load_dotenv
# ---
HOME = os.getenv("HOME")
# ---
env_file_path = f"{HOME}/python/.env" if (HOME and os.path.exists(f"{HOME}/python/.env")) else ".env"
# ---
load_dotenv(env_file_path)
# ---
config = ConfigParser()
# ---
home_dir = HOME if HOME else os.path.expanduser("~")
# ---
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
SVG_DATA_PATH = os.getenv("SVG_DATA_PATH", f"{home_dir}/svg_data")
DB_CONFIG_PATH = os.getenv("DB_CONFIG_PATH", f"{home_dir}/confs/db.ini")
USER_CONFIG_PATH = os.getenv("USER_CONFIG_PATH", f"{home_dir}/confs/user.ini")
LOG_DIR_PATH = os.getenv("LOG_PATH", f"{home_dir}/logs")
DISABLE_UPLOADS = os.getenv("DISABLE_UPLOADS", "1")
# ---
# ---

svg_data_dir = Path(SVG_DATA_PATH)
svg_data_dir.mkdir(parents=True, exist_ok=True)

config.read(DB_CONFIG_PATH)

db_config_section = config['client'] if 'client' in config else config['DEFAULT']

db_data = {
    "host": db_config_section.get('host', ""),
    "user": db_config_section.get('user', ""),
    "dbname": db_config_section.get('dbname', ""),
    "password": db_config_section.get('password', ""),
}
