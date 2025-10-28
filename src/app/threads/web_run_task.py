
import re
import logging
import threading
from pathlib import Path
from typing import Any, Dict

from ..web.start_bot import (
    save_files_stats,
    text_task,
    titles_task,
    translations_task,
    make_results_summary
)
from .inject_tasks import inject_task
from ..download_tasks import download_task
from ..upload_tasks import upload_task
from ..config import settings
from ..db.task_store_pymysql import TaskStorePyMysql

logger = logging.getLogger(__name__)


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
    logger.debug(f"compute_output_dir: {name=}")
    # ---
    # name = death rate from obesity
    slug = re.sub(r'[^A-Za-z0-9._\- ]+', "_", str(name)).strip("._") or "untitled"
    # ---
    out = Path(settings.paths.svg_data) / slug
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
    user_data: Dict[str, str] | None,
    *,
    cancel_event: threading.Event | None = None,
) -> None:
    """Execute the full SVG translation pipeline for a queued task.

    Parameters:
        db_data (dict): Database connection parameters for the task store.
        task_id (str): Identifier of the task being processed.
        title (str): Commons title submitted by the user.
        args: Namespace-like object returned by :func:`parse_args`.
        user_data (dict): Authentication payload used for upload operations.

    Side Effects:
        Updates task records, writes files under ``svg_data_dir``, and interacts
        with external services for downloading and uploading files.
    """
    output_dir = _compute_output_dir(title)
    task_snapshot: Dict[str, Any] = {
        "title": title,
    }

    # store = TaskStorePyMysql(db_data)
    with TaskStorePyMysql(db_data) as store:
        stages_list = make_stages()

        def push_stage(stage_name: str, stage_state: Dict[str, Any] | None = None) -> None:
            """Persist the latest state for a workflow stage to the database."""
            state = stage_state if stage_state is not None else stages_list[stage_name]
            store.update_stage(task_id, stage_name, state)

        store.update_data(task_id, task_snapshot)

        def check_cancel(stage_name: str | None = None) -> bool:
            if cancel_event is None or not cancel_event.is_set():
                return False

            if stage_name:
                stage_state = stages_list.get(stage_name)
                if stage_state and stage_state.get("status") == "Running":
                    stage_state["status"] = "Cancelled"
                    push_stage(stage_name, stage_state)

            stages_list["initialize"]["status"] = "Completed"
            push_stage("initialize")
            store.update_status(task_id, "Cancelled")
            logger.debug(f"Task: {task_id} Cancelled.")
            return True

        if cancel_event is not None and cancel_event.is_set():
            if check_cancel("initialize"):
                return

        store.update_status(task_id, "Running")

        # ----------------------------------------------
        # Stage 1: extract text
        text, stages_list["text"] = text_task(stages_list["text"], title)
        push_stage("text")
        if check_cancel("text"):
            return
        if not text:
            return fail_task(store, task_id, stages_list, "No text extracted")

        # ----------------------------------------------
        # Stage 2: extract titles
        titles_result, stages_list["titles"] = titles_task(
            stages_list["titles"],
            text,
            args.manual_main_title,
            titles_limit=args.titles_limit,
        )

        push_stage("titles")
        if check_cancel("titles"):
            return

        main_title, titles = titles_result["main_title"], titles_result["titles"]

        if not main_title:
            return fail_task(store, task_id, stages_list, "No main title found")

        value = f"File:{main_title}" if not main_title.lower().startswith("file:") else main_title
        store.update_task_one_column(task_id, "main_file", value)

        if not titles:
            return fail_task(store, task_id, stages_list, "No titles found")

        # ----------------------------------------------
        # Stage 3: get translations
        output_dir_main = output_dir / "files"
        output_dir_main.mkdir(parents=True, exist_ok=True)

        translations, stages_list["translations"] = translations_task(stages_list["translations"], main_title, output_dir_main)
        push_stage("translations")
        if check_cancel("translations"):
            return

        if not translations:
            return fail_task(store, task_id, stages_list, "No translations available")

        # ----------------------------------------------
        # Stage 4: download SVG files
        files, stages_list["download"], not_done_list = download_task(
            task_id,
            stages=stages_list["download"],
            output_dir_main=output_dir_main,
            titles=titles,
            store=store,
            check_cancel=check_cancel
        )
        if not_done_list:
            task_snapshot["not_done_list"] = not_done_list
            store.update_data(task_id, task_snapshot)

        push_stage("download")
        if check_cancel("download"):
            return

        if not files:
            return fail_task(store, task_id, stages_list, "No files downloaded")

        # ----------------------------------------------
        # Stage 5: inject translations
        injects_result, stages_list["inject"] = inject_task(
            stages_list["inject"],
            files,
            translations,
            output_dir=output_dir,
            overwrite=args.overwrite
        )
        push_stage("inject")
        if check_cancel("inject"):
            return

        if not injects_result or injects_result.get("saved_done", 0) == 0:
            return fail_task(store, task_id, stages_list, "Injection saved 0 files")

        inject_files = {x: v for x, v in injects_result.get("files", {}).items() if x != main_title}

        # ----------------------------------------------
        # Stage 6: upload results
        files_to_upload = {x: v for x, v in inject_files.items() if v.get("file_path")}

        no_file_path = len(inject_files) - len(files_to_upload)

        upload_result, stages_list["upload"] = upload_task(
            stages_list["upload"],
            files_to_upload,
            main_title,
            do_upload=args.upload,
            user=user_data,
            store=store,
            task_id=task_id,
            check_cancel=check_cancel
        )

        push_stage("upload")
        if check_cancel("upload"):
            return

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

        if check_cancel("initialize"):
            return

        store.update_status(task_id, final_status)
