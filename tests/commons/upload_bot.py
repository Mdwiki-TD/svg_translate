
import sys
import json
import random
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from svg_translate.user_info import username, password
from svg_translate import upload_file

files_stats_path = Path(__file__).parent.parent.parent / "svg_data/files_stats.json"

data = json.load(files_stats_path.open("r", encoding="utf-8"))

main_title_link = f"[[:File:{data['main_title']}]]"

files_keys = list(data["files"].keys())

# shuffle the files
random.shuffle(files_keys)

file_name = files_keys[0]

file_data = data["files"][file_name]
# ---
file_path = file_data["file_path"]
# ---
summary = f"Adding {file_data['new_languages']} languages translations from {main_title_link}"
# ---
print(f"start uploading file: {file_path}")
print(f"{summary=}")
# ---
upload_file(file_name, file_path, site=None, username=username, password=password, summary=summary)
# ---
