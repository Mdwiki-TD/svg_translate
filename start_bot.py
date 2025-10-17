"""

python3 I:/mdwiki/svg_repo/start_bot.py
python3 start_bot.py

tfj run svgbot --image python3.9 --command "$HOME/local/bin/python3 ~/bots/svg_translate/start_bot.py noup"

"""
from pathlib import Path
import sys
import os
import json

from svg_translate import start_on_template_title, config_logger
from svg_translate.upload_files import start_upload

from user_info import username, password

config_logger("CRITICAL")


def one_title(title, output_dir, titles_limit=None, overwrite=False, do_upload=None):
    """
    Run the title workflow and return structured results suitable for a web UI.

    Returns a dict with keys:
    - title, output_dir
    - stages: list of {name, status, message}
    - results: summary numbers
    - files_to_upload: mapping of files prepared for upload (path present)
    - files_data: raw result from start_on_template_title (for diagnostics)
    - error: optional error string if a stage fails
    """

    stages = [
        {"name": "initialize", "status": "in_progress", "message": "Starting workflow"},
        {"name": "process-title", "status": "pending", "message": "Processing template and files"},
        {"name": "upload", "status": "pending", "message": "Uploading translated files"},
        {"name": "complete", "status": "pending", "message": "Finalizing"},
    ]

    result = {
        "title": title,
        "output_dir": str(output_dir),
        "stages": stages,
        "results": {},
        "files_to_upload": {},
        "files_data": None,
    }

    try:
        # Stage: initialize -> completed
        stages[0]["status"] = "completed"

        # Stage: process-title
        stages[1]["status"] = "in_progress"

        files_data = start_on_template_title(
            title, output_dir=output_dir, titles_limit=titles_limit, overwrite=overwrite
        )

        if not files_data:
            stages[1]["status"] = "error"
            stages[1]["message"] = "No data returned for title"
            result["error"] = "no files_data"
            return result

        result["files_data"] = files_data

        translations_new = files_data.get("translations", {}).get("new", {})

        # Prepare upload set and compute counts
        files_map = files_data.get("files") or {}
        if files_map:
            if files_data.get('main_title') in files_map:
                # exclude the main translation source file from uploads
                files_map = {k: v for k, v in files_map.items() if k != files_data['main_title']}

            files_to_upload = {x: v for x, v in files_map.items() if v.get("file_path")}
            no_file_path = len(files_map) - len(files_to_upload)
        else:
            files_to_upload = {}
            no_file_path = 0

        result["files_to_upload"] = files_to_upload

        # Summaries
        results_summary = {
            "total_files": len(files_map),
            "files_to_upload_count": len(files_to_upload),
            "no_file_path": no_file_path,
            "nested_files": files_data.get('nested_files', 0),
            "saved_done": files_data.get('saved_done', 0),
            "no_save": files_data.get('no_save', 0),
            "new_translations_count": len(translations_new),
            "main_title": files_data.get('main_title'),
        }
        result["results"] = results_summary

        stages[1]["status"] = "completed"
        stages[1]["message"] = (
            f"Processed {results_summary['total_files']} files; "
            f"to upload: {results_summary['files_to_upload_count']}"
        )

        # Stage: upload
        stages[2]["status"] = "in_progress" if files_to_upload else "completed"
        stages[2]["message"] = (
            "Uploading files" if files_to_upload else "No files to upload"
        )

        # Determine upload behavior
        if do_upload is None:
            # Preserve legacy behavior: upload unless 'noup' is in argv
            do_upload = ("noup" not in sys.argv)

        uploaded = []
        if files_to_upload and do_upload:
            try:
                main_title_link = f"[[:File:{files_data['main_title']}]]" if files_data.get('main_title') else ""
                start_upload(files_to_upload, main_title_link, username, password)
                stages[2]["status"] = "completed"
                stages[2]["message"] = f"Uploaded {len(files_to_upload)} files"
            except Exception as e:
                stages[2]["status"] = "error"
                stages[2]["message"] = f"Upload failed: {e}"
                result["error"] = f"upload-error: {e}"
        else:
            stages[2]["status"] = "completed"

        # Stage: complete
        stages[3]["status"] = "completed"
        stages[3]["message"] = (
            f"output_dir: {Path(output_dir).name}, "
            f"no_file_path: {results_summary['no_file_path']}, "
            f"nested: {results_summary['nested_files']}, "
            f"translations: {results_summary['new_translations_count']}"
        )

        return result

    except Exception as e:
        # Any uncaught error
        result["error"] = str(e)
        # Mark the first stage that is in progress as errored
        for st in stages:
            if st["status"] == "in_progress":
                st["status"] = "error"
                st["message"] = f"Error: {e}"
                break
        return result


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

    svg_data_dir = Path(__file__).parent / "svg_data"

    if os.getenv("HOME"):
        svg_data_dir = Path(__file__).parent.parent/ "svg_data"

    for title in titles:
        output_dir = svg_data_dir / title.split("/")[1]
        data = one_title(title, output_dir, titles_limit=1000)
        # print a concise summary for CLI usage
        if data:
            print("----" * 15)
            print(json.dumps({
                "title": data.get("title"),
                "results": data.get("results", {}),
                "error": data.get("error"),
            }, indent=2))
        # break


if __name__ == "__main__":
    main()
