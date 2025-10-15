"""

python3 I:/mdwiki/svg_repo/start_bot.py
python3 start_bot.py

tfj run svgbot --image python3.9 --command "$HOME/local/bin/python3 ~/bots/svg_translate/start_bot.py noup"

"""
from tqdm import tqdm
from pathlib import Path
import mwclient
import sys

from svg_translate import start_on_template_title, upload_file, config_logger

from user_info import username, password

config_logger("CRITICAL")
# config_logger("ERROR")


def start_upload(files_to_upload, main_title_link):

    site = mwclient.Site('commons.m.wikimedia.org')

    try:
        site.login(username, password)
    except mwclient.errors.LoginError as e:
        print(f"Could not login error: {e}")

    if site.logged_in:
        print(f"<<yellow>>logged in as {site.username}.")

    for file_name, file_data in tqdm(files_to_upload.items(), desc="uploading files"):
        # ---
        file_path = file_data.get("file_path", None)
        # ---
        print(f"start uploading file: {file_name}.")
        # ---
        summary = f"Adding {file_data['new_languages']} languages translations from {main_title_link}"
        # ---
        upload = upload_file(file_name, file_path, site=site, summary=summary) or {}
        # ---
        print(f"upload: {upload.get('result')}")
        # ---
        # break


def one_title(title, output_dir, titles_limit=None, overwrite=False):

    print("----"*15)
    files_data = start_on_template_title(title, output_dir=output_dir, titles_limit=titles_limit, overwrite=overwrite)

    translations = files_data.get("translations", {}).get("new", {})

    if files_data['files']:
        print(f"len files_data: {len(files_data['files']):,}")

        if files_data['main_title'] in files_data['files']:
            del files_data['files'][files_data['main_title']]

        main_title_link = f"[[:File:{files_data['main_title']}]]"
        files_to_upload = {x: v for x, v in files_data["files"].items() if v.get("file_path", None)}
        print(f"len files_to_upload: {len(files_to_upload):,}")

        no_file_path = len(files_data["files"]) - len(files_to_upload)

        if files_to_upload and "noup" not in sys.argv:
            start_upload(files_to_upload, main_title_link)

        print(f"output_dir: {output_dir.name}, no_file_path: {no_file_path}, nested_files: {files_data['nested_files']:,}, translations: {len(translations):,}")


def main():
    titles = [
        "Template:OWID/share with mental and substance disorders",
        "Template:Owidslider/indoor air pollution",
        # "Template:OWID/maternal mortality",
        "Template:OWID/dalys rate from all causes",
        "Template:OWID/Parkinsons prevalence",
        "Template:OWID/cancer death rates",
        "Template:OWID/overarching legal frameworks regarding gender equality",
        "Template:OWID/share with drug use disorders",
        "Template:OWID/number of deaths from tetanus",
        "Template:OWID/tuberculosis deaths. WHO",
        "Template:OWID/death rates cocaine",
        "Template:OWID/hepatitis c number of deaths",
        "Template:OWID/death rates substance disorders who",
        "Template:OWID/new infections with tetanus",
    ]

    titles = [
        "Template:OWID/Death rate from obesity",
    ]
    svg_data_dir = Path(__file__).parent / "svg_data"

    for title in titles:
        output_dir = svg_data_dir / title.split("/")[1]
        one_title(title, output_dir, titles_limit=1000)
        # break


if __name__ == "__main__":
    main()
