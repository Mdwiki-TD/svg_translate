#
import os
import threading
# import logging
from pathlib import Path
from typing import MutableMapping, Any

from web.start_bot import (
    save_files_stats,
    text_task,
    titles_task,
    translations_task,
    download_task,
    inject_task,
    upload_task,
    make_results_summary
)

from svg_translate import logger

# logger = logging.getLogger(__name__)


def _compute_output_dir(title: str) -> Path:
    # Align with CLI behavior: store under repo svg_data/<slug>
    slug = title.split("/")[-1]
    base = Path(__file__).parent.parent / "svg_data"

    if not os.getenv("HOME"):
        base = Path("I:/SVG/svg_data")

    base.mkdir(parents=True, exist_ok=True)
    return base / slug


def make_stages():
    return {
        "initialize": {
            "number": 1,
            "sub_name": "",
            "status": "Running",
            "message": "Starting workflow"
        },
        "text": {
            "sub_name": "",
            "number": 2,
            "status": "Pending",
            "message": "Getting text"
        },
        "titles": {
            "sub_name": "",
            "number": 3,
            "status": "Pending",
            "message": "Getting titles"
        },
        "translations": {
            "sub_name": "",
            "number": 4,
            "status": "Pending",
            "message": "Getting translations"
        },
        "download": {
            "sub_name": "",
            "number": 5,
            "status": "Pending",
            "message": "Downloading files"
        },
        "inject": {
            "sub_name": "",
            "number": 6,
            "status": "Pending",
            "message": "Injecting translations"
        },
        "upload": {
            "sub_name": "",
            "number": 7,
            "status": "Pending",
            "message": "Uploading files"
        },
    }


def fail_task(tasks, task_id, stages, msg=None):
    """Mark task as failed and log reason."""
    tasks[task_id]["status"] = "Failed"
    stages["initialize"]["status"] = "Completed"
    if msg:
        logger.error(msg)
    return None


# --- main pipeline --------------------------------------------
def run_task(task_id: str, title: str, args: Any, tasks: MutableMapping[str, Any], tasks_lock: threading.Lock) -> None:

    output_dir = _compute_output_dir(title)
    with tasks_lock:
        tasks[task_id]["data"] = {
            "title": title,
            "stages": make_stages()
        }

    stages_list = tasks[task_id]["data"]["stages"]

    # Stage 1: extract text
    text, stages_list["text"] = text_task(stages_list["text"], title)
    if not text:
        with tasks_lock:
            return fail_task(tasks, task_id, stages_list, "No text extracted")

    # Stage 2: extract titles
    titles_result, stages_list["titles"] = titles_task(stages_list["titles"], text, titles_limit=args.titles_limit)

    main_title, titles = titles_result["main_title"], titles_result["titles"]
    if not titles:
        with tasks_lock:
            return fail_task(tasks, task_id, stages_list, "No titles found")

    # Stage 3: get translations
    output_dir_main = output_dir / "files"
    output_dir_main.mkdir(parents=True, exist_ok=True)

    translations, stages_list["translations"] = translations_task(stages_list["translations"], main_title, output_dir_main)

    if not translations:
        with tasks_lock:
            return fail_task(tasks, task_id, stages_list, "No translations available")

    # Stage 4: download SVG files
    files, stages_list["download"] = download_task(stages_list["download"], output_dir_main, titles)

    if not files:
        with tasks_lock:
            return fail_task(tasks, task_id, stages_list, "No files downloaded")

    # Stage 5: inject translations
    injects_result, stages_list["inject"] = inject_task(stages_list["inject"], files, translations, output_dir=output_dir, overwrite=args.overwrite)

    if not injects_result or injects_result.get("saved_done", 0) == 0:
        with tasks_lock:
            return fail_task(tasks, task_id, stages_list, "Injection saved 0 files")

    inject_files = {x: v for x, v in injects_result.get("files", {}).items() if x != main_title}

    files_to_upload = {x: v for x, v in inject_files.items() if v.get("file_path")}

    no_file_path = len(inject_files) - len(files_to_upload)

    # Stage 6: upload results
    upload_result, stages_list["upload"] = upload_task(stages_list["upload"], files_to_upload, main_title, args.upload)

    # Stage 7: save stats and mark done
    data = {
        "main_title": main_title,
        "translations": translations or {},
        "titles": titles,
        "files": files,
        "injects_result": injects_result,
    }

    save_files_stats(data, output_dir)

    with tasks_lock:

        tasks[task_id]["results"] = make_results_summary(len(files), len(files_to_upload), no_file_path, injects_result, translations, main_title, upload_result)

        # Consider any stage failure terminal
        final_status = "Failed" if any(s.get("status") == "Failed" for s in stages_list.values()) else "Completed"
        tasks[task_id]["status"] = final_status

        stages_list["initialize"]["status"] = "Completed"
