"""

python3 I:/SVG/svg_repo/bot.py
python3 start_bot.py

tfj run svgbot --image python3.9 --command "$HOME/local/bin/python3 ~/bots/svg_translate/start_bot.py noup"

"""
import os
from pathlib import Path
import sys


from src.svg_translate import start_on_template_title, config_logger
from src.svg_translate.upload_files import start_upload

from src.app.db import get_user
from src.svg_config import svg_data_dir

config_logger("ERROR")  # DEBUG # ERROR # CRITICAL


def one_title(title, output_dir, titles_limit=None, overwrite=False):
    output_dir = output_dir or svg_data_dir

    print("----"*15)
    files_data = start_on_template_title(title, output_dir=output_dir, titles_limit=titles_limit, overwrite=overwrite)

    if not files_data:
        print("no files_data")
        return None

    translations = files_data.get("translations", {}).get("new", {})

    if not files_data['files']:
        return
    print(f"len files_data: {len(files_data['files']):,}")

    if files_data['main_title'] in files_data['files']:
        del files_data['files'][files_data['main_title']]

    main_title_link = f"[[:File:{files_data['main_title']}]]"
    files_to_upload = {x: v for x, v in files_data["files"].items() if v.get("file_path", None)}
    print(f"len files_to_upload: {len(files_to_upload):,}")

    no_file_path = len(files_data["files"]) - len(files_to_upload)

    if files_to_upload and "noup" not in sys.argv:
        user_id = os.getenv("MW_DEFAULT_USER_ID")
        if not user_id:
            raise SystemExit("MW_DEFAULT_USER_ID environment variable is required for uploads")
        user = get_user(int(user_id))
        if not user:
            raise SystemExit(f"No OAuth credentials found for user id {user_id}")

        upload_result = start_upload(files_to_upload, main_title_link, user["token_enc"])
        # {"done": done, "not_done": not_done, "errors": errors}
        print(f"upload_result: Done: {upload_result['done']:,}, Not done: {upload_result['not_done']:,}, Errors: {len(upload_result['errors']):,}")

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
        "Template:OWID/death rate from obesity",
    ]

    for title in titles:
        # output_dir = svg_data_dir / title.split("/")[1]
        output_dir = svg_data_dir / Path(title).name
        one_title(title, output_dir, titles_limit=1000)
        # break


if __name__ == "__main__":
    main()
