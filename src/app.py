from __future__ import annotations

from collections import namedtuple
from datetime import datetime
from logging import debug
import os
import sys
import threading
import uuid
from typing import Any, Dict, List

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
# from asgiref.wsgi import WsgiToAsgi

from svg_config import SECRET_KEY, db_data, DISABLE_UPLOADS, user_data
from log import logger  # , config_logger
# config_logger("DEBUG")  # DEBUG # ERROR # CRITICAL

from web.web_run_task import run_task
# from uvicorn.main import logger

from web.db.task_store_pymysql import TaskAlreadyExistsError, TaskStorePyMysql

TASK_STORE = TaskStorePyMysql(db_data)
TASKS_LOCK = threading.Lock()

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = SECRET_KEY


def parse_args(request_form: Dict[str, Any]) -> Any:
    """Extract workflow arguments from a Flask request form.

    Parameters:
        request_form (Mapping[str, Any]): The POSTed form data from the request.

    Returns:
        namedtuple: A namespace containing `titles_limit` (int), `overwrite` (bool),
        and `upload` (bool) flags consumed by the background task runner.
    """

    Args = namedtuple("Args", ["titles_limit", "overwrite", "upload", "ignore_existing_task"])
    # ---
    upload = False
    # ---
    if DISABLE_UPLOADS != "1":
        upload = bool(request_form.get("upload"))
    # ---
    result = Args(
        titles_limit=request_form.get("titles_limit", 1000, type=int),
        overwrite=bool(request_form.get("overwrite")),
        ignore_existing_task=bool(request_form.get("ignore_existing_task")),
        upload=upload
    )
    # ---
    return result


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
    if isinstance(value, str):
        for fmt in (None, "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.fromisoformat(value) if fmt is None else datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
    elif isinstance(value, datetime):
        dt = value

    if not dt:
        return str(value), str(value)

    display = dt.strftime("%Y-%m-%d %H:%M:%S")
    sort_key = dt.isoformat()
    return display, sort_key


def _format_task_for_view(task: dict) -> dict:
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
        "user": task.get("user"),
    }


def _order_stages(stages: Dict[str, Any] | None) -> List[tuple[str, Dict[str, Any]]]:
    """Normalize the stage mapping into a sorted list of name/data tuples.

    Parameters:
        stages (Dict[str, Any] | None): Mapping of stage name to metadata or None.

    Returns:
        List[tuple[str, Dict[str, Any]]]: Stage entries sorted by their `number` key; empty
        when `stages` is falsy or lacks valid dict values.
    """

    if not stages:
        return []
    ordered: List[tuple[str, Dict[str, Any]]] = []
    for name, data in stages.items():
        if isinstance(data, dict):
            ordered.append((name, data))
    ordered.sort(key=lambda item: item[1].get("number", 0))
    return ordered


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


@app.get("/task1")
def task1() -> Response:
    """Render the task detail page for the first step of the workflow.

    Returns:
        flask.Response: The rendered template for task step 1, populated with the
        stored task data or an error payload when the task identifier is invalid.
    """

    task_id = request.args.get("task_id")
    task = TASK_STORE.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.warning(f"Task {task_id} not found!!")

    error_message = get_error_message(request.args.get("error"))

    return render_template(
        "task1.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}),
        error_message=error_message,
    )


@app.get("/")
def index() -> Response:
    """Render the landing page for creating a new translation task.

    Returns:
        flask.Response: The rendered `index.html` template, optionally populated
        with an error message when a duplicate task submission was attempted.
    """

    error_message = get_error_message(request.args.get("error"))

    return render_template(
        "index.html",
        form={},
        error_message=error_message,
    )


@app.get("/task2")
def task2() -> Response:
    """Render the progress page for an existing translation task.

    Returns:
        flask.Response: The rendered template for task step 2 with the ordered
        stages list, or an error payload if the task no longer exists.
    """

    task_id = request.args.get("task_id")
    title = request.args.get("title")
    task = TASK_STORE.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.warning(f"Task {task_id} not found!!")

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


@app.post("/")
def start() -> Response:
    """Create a new task for the submitted title and launch the background worker.

    Side Effects:
        Persists a new task record in the database-backed store and spawns a
        daemon thread to execute :func:`web.web_run_task.run_task`.

    Returns:
        flask.Response: Redirects the user to the step-1 view for either the newly
        created task or the existing active task when a duplicate title is
        detected.
    """

    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("index"))

    args = parse_args(request.form)

    task_id = uuid.uuid4().hex

    with TASKS_LOCK:
        logger.warning(f"ignore_existing_task: {args.ignore_existing_task}")
        if not args.ignore_existing_task:
            existing_task = TASK_STORE.get_active_task_by_title(title)

            if existing_task:
                logger.warning(f"Task for title '{title}' already exists: {existing_task['id']}.")
                return redirect(url_for("task1", task_id=existing_task["id"], title=title, error="task-active"))

        try:
            TASK_STORE.create_task(
                task_id,
                title,
                form=request.form.to_dict(flat=True)
            )
        except TaskAlreadyExistsError as exc:
            existing = exc.task
            return redirect(url_for("task1", task_id=existing["id"], title=title, error="task-active"))
        except Exception as exc:  # noqa: BLE001 — TaskStore may surface heterogeneous DB errors
            logger.exception("Failed to create task", exc_info=exc)
            return redirect(url_for("index", title=title, error="task-create-failed"))

    # ---
    t = threading.Thread(
        target=run_task,
        args=(db_data, task_id, title, args, user_data),
        name=f"task-runner-{task_id[:8]}",
        daemon=True
    )
    # ---
    t.start()
    # ---
    return redirect(url_for("task1", title=title, task_id=task_id))


@app.get("/tasks")
def tasks() -> Response:
    """
    Render the task listing page with formatted task metadata and available status filters.

    Retrieve tasks from the global task store, optionally filter by status, and produce a list of task dictionaries with selected fields and display/sortable timestamp values. Also collect the distinct task statuses found and pass the tasks, the current status filter, and the sorted available statuses to the "tasks.html" template.

    Returns:
        A Flask response object rendering "tasks.html" with the context keys `tasks`, `status_filter`, and `available_statuses`.
    """
    status_filter = request.args.get("status")

    with TASKS_LOCK:
        db_tasks = TASK_STORE.list_tasks(status=status_filter, order_by="created_at", descending=True)

    formatted_tasks = [_format_task_for_view(task) for task in db_tasks]
    status_values = {task.get("status") for task in db_tasks if task.get("status")}

    available_statuses = sorted(status_values)

    return render_template(
        "tasks.html",
        tasks=formatted_tasks,
        status_filter=status_filter,
        available_statuses=available_statuses,
    )


@app.get("/status/<task_id>")
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

    task = TASK_STORE.get_task(task_id)
    if not task:
        logger.warning(f"Task {task_id} not found")
        return jsonify({"error": "not-found"}), 404

    return jsonify(task)


if __name__ == "__main__":
    debug = "debug" in sys.argv
    app.run(debug=debug)
