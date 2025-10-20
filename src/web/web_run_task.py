#
# import os
import re
# import logging
from pathlib import Path
from typing import Any, Dict

from web.start_bot import (
    save_files_stats,
    text_task,
    titles_task,
    translations_task,
    inject_task,
    make_results_summary
)
from web.download_task import download_task
from web.upload_task import upload_task

from svg_config import svg_data_dir
from svg_translate import logger
from web.db.task_store_pymysql import TaskStorePyMysql

# logger = logging.getLogger(__name__)


def _compute_output_dir(title: str) -> Path:
    # Align with CLI behavior: store under repo svg_data/<slug>
    # Use last path segment and sanitize for filesystem safety
    name = Path(title).name
    # ---
    slug = re.sub(r'[^A-Za-z0-9._-]+', "_", name).strip("._") or "untitled"
    # ---
    out = svg_data_dir / slug
    # ---
    out.mkdir(parents=True, exist_ok=True)
    # ---
    return out


def make_stages():
    """
    Create an initial stages dictionary describing progress metadata for the workflow.

    Returns:
        dict: Mapping of stage names ('initialize', 'text', 'titles', 'translations', 'download', 'inject', 'upload')
        to metadata objects with the keys:
          - 'number' (int): stage order,
          - 'sub_name' (str): optional sub-stage name,
          - 'status' (str): current stage status (e.g., "Running", "Pending"),
          - 'message' (str): human-readable status message.
    """
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


def fail_task(store: TaskStorePyMysql, task_id: str, snapshot: Dict[str, Any], msg: str | None = None):
    """
    Mark the task as failed in the provided TaskStore and log an optional error message.

    This sets the `"initialize"` stage status to `"Completed"`, persists the updated snapshot via the store, and marks the task status as `"Failed"`.

    Parameters:
        snapshot (Dict[str, Any]): Current task snapshot; must contain a `"stages"` mapping.
        msg (str | None): Optional error message to log.
    """
    stages = snapshot["stages"]
    stages["initialize"]["status"] = "Completed"
    store.update_data(task_id, snapshot)
    store.update_status(task_id, "Failed")
    if msg:
        logger.error(msg)
    return None


# --- main pipeline --------------------------------------------
def run_task(db_data, task_id: str, title: str, args: Any) -> None:
    output_dir = _compute_output_dir(title)
    task_snapshot: Dict[str, Any] = {
        "title": title,
        "stages": make_stages(),
    }

    store = TaskStorePyMysql(db_data)

    # TODO:
    """
        After each processing stage, the entire task_snapshot is serialized to JSON and written to the database. This is inefficient and results in many database writes. For better performance, consider introducing more granular update methods in TaskStore to update only the parts of the task data that have changed, such as the status of a specific stage. This would reduce I/O and JSON serialization overhead.

        For example, you could add a method update_stage(task_id, stage_name, stage_data) to TaskStore and call it after each step instead of update_data.

        store.update_data(task_id, task_snapshot)
    """
    store.update_data(task_id, task_snapshot)
    store.update_status(task_id, "Running")

    stages_list = task_snapshot["stages"]

    # Stage 1: extract text
    text, stages_list["text"] = text_task(stages_list["text"], title)
    store.update_data(task_id, task_snapshot)
    if not text:
        return fail_task(store, task_id, task_snapshot, "No text extracted")

    # Stage 2: extract titles
    titles_result, stages_list["titles"] = titles_task(stages_list["titles"], text, titles_limit=args.titles_limit)
    store.update_data(task_id, task_snapshot)

    main_title, titles = titles_result["main_title"], titles_result["titles"]
    if not titles:
        return fail_task(store, task_id, task_snapshot, "No titles found")

    # Stage 3: get translations
    output_dir_main = output_dir / "files"
    output_dir_main.mkdir(parents=True, exist_ok=True)

    translations, stages_list["translations"] = translations_task(stages_list["translations"], main_title, output_dir_main)
    store.update_data(task_id, task_snapshot)

    if not translations:
        return fail_task(store, task_id, task_snapshot, "No translations available")

    # Stage 4: download SVG files
    def download_progress(stages):
        return store.update_data(task_id, task_snapshot)

    files, stages_list["download"] = download_task(
        stages_list["download"],
        output_dir_main,
        titles,
        progress_updater=download_progress,
    )
    store.update_data(task_id, task_snapshot)

    if not files:
        return fail_task(store, task_id, task_snapshot, "No files downloaded")

    # Stage 5: inject translations
    injects_result, stages_list["inject"] = inject_task(stages_list["inject"], files, translations, output_dir=output_dir, overwrite=args.overwrite)
    store.update_data(task_id, task_snapshot)

    if not injects_result or injects_result.get("saved_done", 0) == 0:
        return fail_task(store, task_id, task_snapshot, "Injection saved 0 files")

    inject_files = {x: v for x, v in injects_result.get("files", {}).items() if x != main_title}

    files_to_upload = {x: v for x, v in inject_files.items() if v.get("file_path")}

    no_file_path = len(inject_files) - len(files_to_upload)

    # Stage 6: upload results
    def upload_progress():
        return store.update_data(task_id, task_snapshot)

    upload_result, stages_list["upload"] = upload_task(
        stages_list["upload"],
        files_to_upload,
        main_title,
        do_upload=args.upload,
        progress_updater=upload_progress,
    )
    store.update_data(task_id, task_snapshot)

    # Stage 7: save stats and mark done
    data = {
        "main_title": main_title,
        "translations": translations or {},
        "titles": titles,
        "files": files,
        "injects_result": injects_result,
    }

    save_files_stats(data, output_dir)

    results = make_results_summary(
        len(files),
        len(files_to_upload),
        no_file_path,
        injects_result,
        translations,
        main_title,
        upload_result
    )

    store.update_results(task_id, results)

    final_status = "Failed" if any(s.get("status") == "Failed" for s in stages_list.values()) else "Completed"
    stages_list["initialize"]["status"] = "Completed"

    store.update_data(task_id, task_snapshot)
    store.update_status(task_id, final_status)
