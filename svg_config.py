"""

from svg_config import TASK_DB_PATH, SECRET_KEY
from svg_config import user_config_path
from svg_config import svg_data_dir

"""
import os
from pathlib import Path

TASK_DB_PATH = os.getenv("TASK_DB_PATH", "tasks.sqlite3")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
# ---
home_dir = os.getenv("HOME")
project = home_dir if home_dir else 'I:/core/bots/core1'
# ---
user_config_path = f"{project}/confs/user.ini"

# data_path = Path(__file__).parent.parent / "svg_data"
data_path = f"{home_dir}/svg_data" if home_dir else "I:/SVG/svg_data"

svg_data_dir = Path(data_path)
svg_data_dir.mkdir(parents=True, exist_ok=True)
