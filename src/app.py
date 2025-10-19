from __future__ import annotations

from collections import namedtuple
from datetime import datetime
from logging import debug
import sys
import threading
import uuid
from collections import namedtuple
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, render_template, request, redirect, url_for, jsonify
# from asgiref.wsgi import WsgiToAsgi

from web.web_run_task import run_task
# from uvicorn.main import logger
# import logging
# logger = logging.getLogger(__name__)

from svg_translate import logger, config_logger
from web.task_store_pymysql import TaskAlreadyExistsError, TaskStorePyMysql
from svg_config import SECRET_KEY

config_logger("DEBUG")  # DEBUG # ERROR # CRITICAL

TASK_STORE = TaskStorePyMysql()

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = SECRET_KEY


def parse_args(request_form):
    Args = namedtuple("Args", ["titles_limit", "overwrite", "upload"])
    # ---
    upload = bool(request_form.get("upload"))
    # ---
    upload = False
    # ---
    result = Args(
        titles_limit=request_form.get("titles_limit", 1000, type=int),
        overwrite=bool(request_form.get("overwrite")),
        upload=upload
    )
    # ---
    return result


@app.get("/")
def index():
    """
    Render the index page for a task, showing task details and an optional error message.

    Reads the `task_id` and `error` query parameters from the request. If `task_id` is provided, attempts to fetch the corresponding task from the task store; if no task is found, supplies a placeholder task with an `"error": "not-found"` value. Maps the `"task-active"` error code to a human-facing message.

    Returns:
        Rendered HTML response for the index page containing the task data, the task's form values (if any), and an optional error message.
    """
    task_id = request.args.get("task_id")
    task = TASK_STORE.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    error_code = request.args.get("error")
    error_message = None
    if error_code == "task-active":
        error_message = "A task for this title is already in progress."

    stages = _order_stages(task.get("stages") if isinstance(task, dict) else None)

    return render_template(
        "index.html",
        task_id=task_id,
        task=task,
        stages=stages,
        form=task.get("form", {}),
        error_message=error_message,
    )


@app.post("/")
def start():
    """
    Create a new task from the submitted form, start its background worker, and redirect to the task page.

    If the form's title is empty the request is redirected back to the index. On task creation conflict redirects to the existing task with error "task-active". On other creation failures redirects to the index with error "task-create-failed". When creation succeeds a daemon thread is started to run the task and the user is redirected to the new task's index page.

    Returns:
        A Flask redirect response to the index view for the created task, or to the index view with an error code if creation failed or the task already exists.
    """
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("index"))

    # existing_task = TASK_STORE.get_active_task_by_title(title)
    # if existing_task: return redirect(url_for("index", task_id=existing_task["id"], error="task-active"))

    task_id = uuid.uuid4().hex

    try:
        TASK_STORE.create_task(
            task_id,
            title,
            form={x: request.form.get(x) for x in request.form}
        )
    except TaskAlreadyExistsError as exc:
        existing = exc.task
        return redirect(url_for("index", task_id=existing["id"], error="task-active"))
    except Exception as exc:
        logger.exception(f"Failed to create task: {exc}")
        return redirect(url_for("index", error="task-create-failed"))

    args = parse_args(request.form)
    # ---
    t = threading.Thread(target=run_task, args=(TASK_STORE, task_id, title, args), daemon=True)
    # # ---
    t.start()

    return redirect(url_for("index", task_id=task_id))


@app.get("/index2")
def index2():
    """
    Render the index2 page for a task identified by the `task_id` query parameter.

    Fetches the task specified by the `task_id` query parameter and renders the "index2.html" template with the task data, form data (empty dict if absent), and an optional human-readable error message. If no matching task is found, a placeholder task with an error code is used. The query parameter `error=task-active` maps to a user-facing message indicating a task with the same title is already in progress.

    @returns:
        Flask response containing the rendered "index2.html" page populated with `task_id`, `task`, `form`, and `error_message`.
    """
    task_id = request.args.get("task_id")
    task = TASK_STORE.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found")

    error_code = request.args.get("error")
    error_message = None
    if error_code == "task-active":
        error_message = "A task for this title is already in progress."

    stages = _order_stages(task.get("stages") if isinstance(task, dict) else None)

    return render_template(
        "index2.html",
        task_id=task_id,
        task=task,
        stages=stages,
        form=task.get("form", {}),
        error_message=error_message,
    )


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
    }


def _order_stages(stages: Dict[str, Any] | None) -> List[tuple[str, Dict[str, Any]]]:
    if not stages:
        return []
    ordered: List[tuple[str, Dict[str, Any]]] = []
    for name, data in stages.items():
        if isinstance(data, dict):
            ordered.append((name, data))
    ordered.sort(key=lambda item: item[1].get("number", 0))
    return ordered


@app.get("/tasks")
def tasks():
    """
    Render the task listing page with formatted task metadata and available status filters.

    Retrieve tasks from the global task store, optionally filter by status, and produce a list of task dictionaries with selected fields and display/sortable timestamp values. Also collect the distinct task statuses found and pass the tasks, the current status filter, and the sorted available statuses to the "tasks.html" template.

    Returns:
        A Flask response object rendering "tasks.html" with the context keys `tasks`, `status_filter`, and `available_statuses`.
    """
    status_filter = request.args.get("status")
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
    task = TASK_STORE.get_task(task_id)
    if not task:
        logger.debug(f"Task {task_id} not found")
        return jsonify({"error": "not-found"}), 404
    return jsonify(task)


if __name__ == "__main__":
    debug = "debug" in sys.argv
    app.run(debug=debug)
