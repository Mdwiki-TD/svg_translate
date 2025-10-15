
import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from commons.user_info import username, password
from commons.upload_bot import upload_file

files_stats_path = Path(__file__).parent.parent.parent / "svg_data/files_stats.json"

data = json.load(files_stats_path.open("r", encoding="utf-8"))

file_name = None
file_path = None

main_title_link = f"[[:File:{data['main_title']}]]"

for file_name, file_data in data["files"].items():
    # ---
    file_path = file_data["file_path"]
    # ---
    summary = f"Adding {file_data['new_languages']} languages translations from {main_title_link}"
    # ---
    print(f"start uploading file: {file_name}.")
    # ---
    upload_file(file_name, file_path, site=None, username=username, password=password, summary=None)
    # ---
    break
