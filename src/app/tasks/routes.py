from __future__ import annotations

from collections import namedtuple
from datetime import datetime
import threading
import uuid
import logging
from typing import Any, Dict, List

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from ..config import settings
from ..svg_config import DISABLE_UPLOADS
from ..web.web_run_task import run_task
from ..db.task_store_pymysql import TaskAlreadyExistsError, TaskStorePyMysql
from ..users.current import current_user, oauth_required

TASK_STORE: TaskStorePyMysql | None = None
TASKS_LOCK = threading.Lock()

bp_main = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


def parse_args(request_form) -> Any:
    Args = namedtuple("Args", ["titles_limit", "overwrite", "upload", "ignore_existing_task"])
    # ---
    upload = False
    # ---
    if DISABLE_UPLOADS != "1":
        upload = bool(request_form.get("upload"))
    # ---
    return Args(
        titles_limit=request_form.get("titles_limit", 1000, type=int),
        overwrite=bool(request_form.get("overwrite")),
        ignore_existing_task=bool(request_form.get("ignore_existing_task")),
        upload=upload
    )


def get_error_message(error_code: str | None) -> str:
    if not error_code:
        return ""
    # ---
    messages = {
        "task-active": "A task for this title is already in progress.",
        "not-found": "Task not found.",
        "task-create-failed": "Task creation failed.",
    }
    # ---
    return messages.get(error_code, error_code)


def _task_store() -> TaskStorePyMysql:
    global TASK_STORE
    if TASK_STORE is None:
        TASK_STORE = TaskStorePyMysql(settings.db_data)
    return TASK_STORE


def close_task_store() -> None:
    """Close the cached :class:`TaskStorePyMysql` instance if present."""

    if TASK_STORE is not None:
        TASK_STORE.close()


def _task_lock() -> threading.Lock:
    global TASKS_LOCK
    if TASKS_LOCK is None:
        TASKS_LOCK = threading.Lock()
    return TASKS_LOCK


def _format_timestamp(value: datetime | str | None) -> tuple[str, str]:
    """
    Format a timestamp value for user display and provide a sortable ISO-style key.

    Parameters:
        value (datetime | str | None): The timestamp to format. May be a datetime, a string (ISO format or "%Y-%m-%d %H:%M:%S"), or None.

    Returns:
        tuple[str, str]: A pair (display, sort_key).
            - display: human-readable timestamp in "YYYY-MM-DD HH:MM:SS", an empty string if `value` is None, or the original string if it could not be parsed.
            - sort_key: an ISO-format timestamp suitable for sorting, an empty string if `value` is None, or the original string if it could not be parsed.
    """
    if not value:
        return "", ""
    dt = None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        for fmt in (None, "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.fromisoformat(value) if fmt is None else datetime.strptime(value, fmt)
                break
            except (TypeError, ValueError):
                continue

    if not dt:
        return str(value), str(value)

    display = dt.strftime("%Y-%m-%d %H:%M:%S")
    sort_key = dt.isoformat()
    return display, sort_key


def _format_task(task: dict) -> dict:
    """Formats a task dictionary for the tasks list view."""
    results = task.get("results") or {}
    injects = results.get("injects_result") or {}

    created_display, created_sort = _format_timestamp(task.get("created_at"))
    updated_display, updated_sort = _format_timestamp(task.get("updated_at"))

    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "status": task.get("status"),
        "files_to_upload_count": results.get("files_to_upload_count", 0),
        "new_translations_count": results.get("new_translations_count", 0),
        "total_files": results.get("total_files", 0),
        "nested_files": injects.get("nested_files", 0),
        "created_at_display": created_display,
        "created_at_sort": created_sort,
        "updated_at_display": updated_display,
        "updated_at_sort": updated_sort,
        "username": task.get("username", "")
    }


def _order_stages(stages: Dict[str, Any] | None) -> List[tuple[str, Dict[str, Any]]]:
    if not stages:
        return []
    ordered = [
        (name, data)
        for name, data in stages.items()
        if isinstance(data, dict)
    ]
    ordered.sort(key=lambda item: item[1].get("number", 0))
    return ordered


def _get_task_store() -> TaskStorePyMysql:
    global TASK_STORE
    if TASK_STORE is None:
        TASK_STORE = TaskStorePyMysql(settings.db_data)
    return TASK_STORE


@bp_main.get("/task1")
def task1():
    task_id = request.args.get("task_id")
    store = _get_task_store()
    task = store.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    error_message = get_error_message(request.args.get("error"))

    return render_template(
        "task1.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}),
        error_message=error_message,
    )


@bp_main.get("/")
def index():
    error_message = get_error_message(request.args.get("error"))

    return render_template(
        "index.html",
        form={},
        error_message=error_message,
    )


@bp_main.get("/task2")
def task2():
    task_id = request.args.get("task_id")
    title = request.args.get("title")
    store = _get_task_store()
    task = store.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    error_message = get_error_message(request.args.get("error"))

    stages = _order_stages(task.get("stages") if isinstance(task, dict) else None)

    return render_template(
        "task2.html",
        task_id=task_id,
        title=title or task.get("title", ""),
        task=task,
        stages=stages,
        form=task.get("form", {}),
        error_message=error_message,
    )


@bp_main.post("/")
@oauth_required
def start():
    user = current_user()
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("main.index"))

    task_id = uuid.uuid4().hex

    store = _get_task_store()

    args = parse_args(request.form)

    with TASKS_LOCK:
        logger.info(f"ignore_existing_task: {args.ignore_existing_task}")
        if not args.ignore_existing_task:
            existing_task = store.get_active_task_by_title(title)

            if existing_task:
                logger.debug(f"Task for title '{title}' already exists: {existing_task['id']}.")
                return redirect(url_for("main.task1", task_id=existing_task["id"], title=title, error="task-active"))

        try:
            store.create_task(
                task_id,
                title,
                username=(user.username if user else ""),
                form=request.form.to_dict(flat=True)
            )
        except TaskAlreadyExistsError as exc:
            existing = exc.task
            return redirect(url_for("main.task1", task_id=existing["id"], title=title, error="task-active"))
        except Exception:
            logger.exception("Failed to create task")
            return redirect(url_for("main.index", title=title, error="task-create-failed"))

    user_payload: Dict[str, Any] = {}
    if user:
        user_payload = {
            "id": user.user_id,
            "username": user.username,
            "access_token": user.access_token,
            "access_secret": user.access_secret,
        }

    t = threading.Thread(
        target=run_task,
        args=(settings.db_data, task_id, title, args, user_payload),
        name=f"task-runner-{task_id[:8]}",
        daemon=True,
    )
    t.start()

    return redirect(url_for("main.task1", title=title, task_id=task_id))


@bp_main.get("/tasks")
def tasks():
    """
    Render the task listing page with formatted task metadata and available status filters.

    Retrieve tasks from the global task store, optionally filter by status, and produce a list of task dictionaries with selected fields and display/sortable timestamp values. Also collect the distinct task statuses found and pass the tasks, the current status filter, and the sorted available statuses to the "tasks.html" template.

    Returns:
        A Flask response object rendering "tasks.html" with the context keys `tasks`, `status_filter`, and `available_statuses`.
    """
    status_filter = request.args.get("status")

    with TASKS_LOCK:
        db_tasks = _get_task_store().list_tasks(status=status_filter, order_by="created_at", descending=True)

    formatted_tasks = [_format_task(task) for task in db_tasks]
    status_values = {task.get("status") for task in db_tasks if task.get("status")}

    available_statuses = sorted(status_values)

    return render_template(
        "tasks.html",
        tasks=formatted_tasks,
        status_filter=status_filter,
        available_statuses=available_statuses,
    )


@bp_main.get("/status/<task_id>")
def status(task_id: str):
    """
    Return the JSON representation of the task identified by `task_id`.

    Parameters:
        task_id (str): Identifier of the task to retrieve.

    Returns:
        A JSON response containing the task data when found. If no task exists for `task_id`, a JSON error `{"error": "not-found"}` is returned with HTTP status 404.
    """
    if not task_id:
        logger.error("No task_id provided in status request.")
        return jsonify({"error": "no-task-id"}), 400

    task = _get_task_store().get_task(task_id)
    if not task:
        logger.debug(f"Task {task_id} not found")
        return jsonify({"error": "not-found"}), 404

    return jsonify(task)
