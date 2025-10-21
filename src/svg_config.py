"""

"""
import os
from configparser import ConfigParser
from pathlib import Path
# ---
from dotenv import load_dotenv
load_dotenv()
# ---
config = ConfigParser()
# ---
home_dir = os.getenv("HOME") if os.getenv("HOME") else os.path.expanduser("~")
# ---
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

db_config_path = DB_CONFIG_PATH
user_config_path = USER_CONFIG_PATH
