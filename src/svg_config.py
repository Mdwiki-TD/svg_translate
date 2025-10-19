"""

from svg_config import db_data
from svg_config import TASK_DB_PATH, SECRET_KEY
from svg_config import user_config_path
from svg_config import svg_data_dir

"""
import os
from configparser import ConfigParser
from pathlib import Path
# ---
home_dir = os.getenv("HOME")
# ---
project = 'I:/SVG/svg_repo'
project_www = 'I:/SVG/svg_repo'
# ---
if home_dir:
    project = home_dir
    project_www = f"{home_dir}/www"
# ---
TASK_DB_PATH = os.getenv("TASK_DB_PATH", f"{project_www}/tasks.sqlite3")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

user_config_path = f"{project}/confs/user.ini"
db_config_path = f"{project}/confs/db.ini"

# data_path = Path(__file__).parent.parent / "svg_data"
data_path = "I:/SVG/svg_data"

if home_dir:
    data_path = f"{project_www}/svg_data"

svg_data_dir = Path(data_path)
svg_data_dir.mkdir(parents=True, exist_ok=True)

config = ConfigParser()
config.read(f"{project}/confs/db.ini")

DEFAULT = config['DEFAULT']

if not DEFAULT:
    DEFAULT = config['client']
db_data = {
    "host": DEFAULT.get('host', ""),
    "user": DEFAULT.get('user', ""),
    "dbname": DEFAULT.get('dbname', ""),
    "password": DEFAULT.get('password', ""),
}
