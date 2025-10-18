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
            "status": "pending",
            "message": "Getting text"
        },
        "titles": {
            "sub_name": "",
            "number": 3,
            "status": "pending",
            "message": "Getting titles"
        },
        "translations": {
            "sub_name": "",
            "number": 4,
            "status": "pending",
            "message": "Getting translations"
        },
        "download": {
            "sub_name": "",
            "number": 5,
            "status": "pending",
            "message": "Downloading files"
        },
        "inject": {
            "sub_name": "",
            "number": 6,
            "status": "pending",
            "message": "Injecting translations"
        },
        "upload": {
            "sub_name": "",
            "number": 7,
            "status": "pending",
            "message": "Uploading files"
        },
    }


def run_task(
    task_id: str,
    title: str,
    args: Any,
    tasks: MutableMapping[str, Any],
    tasks_lock: threading.Lock,
) -> None:

    output_dir = _compute_output_dir(title)
    # ---
    tasks[task_id]["data"] = {
        "title": title,
        "stages": make_stages()
    }
    # ---
    stages_list = tasks[task_id]["data"]["stages"]
    # ---
    text, stages_list["text"] = text_task(stages_list["text"], title)
    # ---
    if not text:
        tasks[task_id]["status"] = "Failed"
        stages_list["initialize"]["status"] = "Completed"
        return
    # ---
    main_title, titles, stages_list["titles"] = titles_task(stages_list["titles"], text, titles_limit=args.titles_limit)
    # ---
    if not titles:
        tasks[task_id]["status"] = "Failed"
        stages_list["initialize"]["status"] = "Completed"
        return
    # ---
    output_dir_main = output_dir / "files"
    output_dir_main.mkdir(parents=True, exist_ok=True)
    # ---
    translations, stages_list["translations"] = translations_task(stages_list["translations"], main_title, output_dir_main)
    # ---
    if not translations:
        tasks[task_id]["status"] = "Failed"
        stages_list["initialize"]["status"] = "Completed"
        return
    # ---
    files, stages_list["download"] = download_task(stages_list["download"], output_dir_main, titles)
    # ---
    if not files:
        tasks[task_id]["status"] = "Failed"
        stages_list["initialize"]["status"] = "Completed"
        return
    # ---
    injects_result, stages_list["inject"] = inject_task(stages_list["inject"], files, translations, output_dir=output_dir, overwrite=args.overwrite)
    # ---
    if injects_result.get('saved_done', 0) == 0:
        tasks[task_id]["status"] = "Failed"
        stages_list["initialize"]["status"] = "Completed"
        logger.error("inject result saved 0 files")
        return
    # ---
    inject_files = {x: v for x, v in injects_result.get("files", {}).items() if x != main_title}
    # ---
    files_to_upload = {x: v for x, v in inject_files.items() if v.get("file_path")}
    # ---
    no_file_path = len(inject_files) - len(files_to_upload)
    # ---
    data = {
        "main_title": main_title,
        "translations": translations or {},
        "titles": titles,
        "files": files,
        "injects_result": injects_result,
    }
    # ---
    save_files_stats(data, output_dir)
    # ---
    upload_result, stages_list["upload"] = upload_task(stages_list["upload"], files_to_upload, main_title, args.upload)
    # ---
    with tasks_lock:
        # ---
        tasks[task_id]["results"] = make_results_summary(len(files), len(files_to_upload), no_file_path, injects_result, translations, main_title, upload_result)
        # ---
        tasks[task_id]["status"] = "Completed" if not data.get("error") else "error"
        # ---
        stages_list["initialize"]["status"] = "Completed"
