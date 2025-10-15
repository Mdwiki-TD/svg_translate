"""

python3 I:/mdwiki/svg_repo/start_bot.py
python3 start_bot.py

"""
from pathlib import Path
import mwclient

from svg_translate import start_on_template_title, upload_file

from user_info import username, password


def main(title):
    output_dir = Path(__file__).parent / "svg_data"

    files_data = start_on_template_title(title, output_dir=output_dir, titles_limit=None, overwrite=False)

    print(f"len files_data: {len(files_data):,}")

    site = mwclient.Site('commons.m.wikimedia.org')

    try:
        site.login(username, password)
    except mwclient.errors.LoginError as e:
        print(f"Could not login error: {e}")

    if site.logged_in:
        print(f"<<yellow>>logged in as {site.username}.")

    main_title_link = f"[[:File:{files_data['main_title']}]]"

    for file_name, file_data in files_data["files"].items():
        file_path = file_data["file_path"]
        # ---
        summary = f"Adding {file_data['new_languages']} languages translations from {main_title_link}"
        # ---
        print(f"start uploading file: {file_name}.")
        # ---
        upload = upload_file(file_name, file_path, site=site, summary=summary)
        # ---
        print(f"upload: {upload}")
        # ---
        break


if __name__ == "__main__":
    title = "Template:OWID/Parkinsons prevalence"
    new_data_paths = main(title)
