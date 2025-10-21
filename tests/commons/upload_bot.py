
import os
import sys
import json
import random
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.app.users.store import get_user_token
from src.app.wiki_client import build_site_for_user
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
user_id = os.getenv("MW_DEFAULT_USER_ID")
if not user_id:
    raise SystemExit("MW_DEFAULT_USER_ID environment variable is required for OAuth uploads")

user = get_user_token(int(user_id))
if not user:
    raise SystemExit(f"No OAuth credentials found for user id {user_id}")

site = build_site_for_user(user)

upload_file(file_name, file_path, site=site, summary=summary)
# ---
