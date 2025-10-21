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
try:  # pragma: no cover - maintain compatibility with both package layouts
    from svg_translate.log import logger
except ImportError:  # pragma: no cover
    from src.svg_translate.log import logger  # type: ignore[no-redef]
from web.db.task_store_pymysql import TaskStorePyMysql

# logger = logging.getLogger(__name__)


def _compute_output_dir(title: str) -> Path:
    """Return the filesystem directory used to store intermediate task output.

    Parameters:
        title (str): User-provided title for the translation task.

    Returns:
        pathlib.Path: Directory path under ``svg_data_dir`` named after a
        sanitized slug derived from ``title``. The directory is created if
        missing.
    """

    # Align with CLI behavior: store under repo svg_data/<slug>
    # Use last path segment and sanitize for filesystem safety
    name = Path(title).name
    # ---
    slug = re.sub(r'[^A-Za-z0-9._\- ]+', "_", name).strip("._") or "untitled"
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


def fail_task(
    store: TaskStorePyMysql,
    task_id: str,
    stages: Dict[str, Dict[str, Any]],
    msg: str | None = None,
):
    """
    Mark the task as failed in the provided TaskStore and log an optional error message.

    This sets the `"initialize"` stage status to `"Completed"`, persists the updated snapshot via the store, and marks the task status as `"Failed"`.

    Parameters:
        snapshot (Dict[str, Any]): Current task snapshot; must contain a `"stages"` mapping.
        msg (str | None): Optional error message to log.
    """
    stages["initialize"]["status"] = "Completed"
    store.update_stage(task_id, "initialize", stages["initialize"])
    store.update_status(task_id, "Failed")
    if msg:
        logger.error(msg)
    return None


# --- main pipeline --------------------------------------------
def run_task(
    db_data: Dict[str, str],
    task_id: str,
    title: str,
    args: Any,
    oauth_credentials: Dict[str, str] | None,
) -> None:
    """Execute the full SVG translation pipeline for a queued task.

    Parameters:
        db_data (dict): Database connection parameters for the task store.
        task_id (str): Identifier of the task being processed.
        title (str): Commons title submitted by the user.
        args: Namespace-like object returned by :func:`web.views.main.parse_args`.
        oauth_credentials (dict | None): Authentication payload used for upload operations.

    Side Effects:
        Updates task records, writes files under ``svg_data_dir``, and interacts
        with external services for downloading and uploading files.
    """
    output_dir = _compute_output_dir(title)
    task_snapshot: Dict[str, Any] = {
        "title": title,
    }

    store = TaskStorePyMysql(db_data)

    stages_list = make_stages()

    # store.replace_stages(task_id, stages_list)

    store.update_data(task_id, task_snapshot)
    store.update_status(task_id, "Running")

    def push_stage(stage_name: str, stage_state: Dict[str, Any] | None = None) -> None:
        """Persist the latest state for a workflow stage to the database."""
        state = stage_state if stage_state is not None else stages_list[stage_name]
        store.update_stage(task_id, stage_name, state)

    # ----------------------------------------------
    # Stage 1: extract text
    text, stages_list["text"] = text_task(stages_list["text"], title)
    push_stage("text")
    if not text:
        return fail_task(store, task_id, stages_list, "No text extracted")

    # ----------------------------------------------
    # Stage 2: extract titles
    titles_result, stages_list["titles"] = titles_task(stages_list["titles"], text, titles_limit=args.titles_limit)
    push_stage("titles")

    main_title, titles = titles_result["main_title"], titles_result["titles"]

    if not titles:
        return fail_task(store, task_id, stages_list, "No titles found")

    if not main_title:
        return fail_task(store, task_id, stages_list, "No main title found")
    # ----------------------------------------------
    # Stage 3: get translations
    output_dir_main = output_dir / "files"
    output_dir_main.mkdir(parents=True, exist_ok=True)

    translations, stages_list["translations"] = translations_task(stages_list["translations"], main_title, output_dir_main)
    push_stage("translations")

    if not translations:
        return fail_task(store, task_id, stages_list, "No translations available")

    # ----------------------------------------------
    # Stage 4: download SVG files
    def download_progress(stage_state: Dict[str, Any]) -> None:
        """Forward download progress updates to the task store."""
        state = stage_state if stage_state is not None else stages_list["download"]
        store.update_stage(task_id, "download", state)

    files, stages_list["download"] = download_task(
        stages_list["download"],
        output_dir_main,
        titles,
        progress_updater=download_progress,
    )
    push_stage("download")

    if not files:
        return fail_task(store, task_id, stages_list, "No files downloaded")

    # ----------------------------------------------
    # Stage 5: inject translations
    injects_result, stages_list["inject"] = inject_task(stages_list["inject"], files, translations, output_dir=output_dir, overwrite=args.overwrite)
    push_stage("inject")

    if not injects_result or injects_result.get("saved_done", 0) == 0:
        return fail_task(store, task_id, stages_list, "Injection saved 0 files")

    inject_files = {x: v for x, v in injects_result.get("files", {}).items() if x != main_title}

    # ----------------------------------------------
    # Stage 6: upload results
    files_to_upload = {x: v for x, v in inject_files.items() if v.get("file_path")}

    no_file_path = len(inject_files) - len(files_to_upload)

    def upload_progress(stage_state: Dict[str, Any]) -> None:
        """Forward upload progress updates to the task store."""
        push_stage("upload", stage_state)

    upload_result, stages_list["upload"] = upload_task(
        stages_list["upload"],
        files_to_upload,
        main_title,
        do_upload=args.upload,
        oauth_credentials=oauth_credentials or {},
        progress_updater=upload_progress,
    )
    push_stage("upload")

    # ----------------------------------------------
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
    push_stage("initialize")

    store.update_status(task_id, final_status)
