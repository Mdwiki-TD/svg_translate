from __future__ import annotations

from collections import namedtuple
from datetime import datetime
from logging import debug
import sys
import threading
import uuid

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

TASK_STORE_New = TaskStorePyMysql()

app = Flask(__name__, template_folder="web/templates")
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
    task_id = request.args.get("task_id")
    task = TASK_STORE_New.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    error_code = request.args.get("error")
    error_message = None
    if error_code == "task-active":
        error_message = "A task for this title is already in progress."

    return render_template(
        "index.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}),
        error_message=error_message,
    )


@app.post("/")
def start():
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("index"))

    # existing_task = TASK_STORE_New.get_active_task_by_title(title)
    # if existing_task: return redirect(url_for("index", task_id=existing_task["id"], error="task-active"))

    task_id = uuid.uuid4().hex

    try:
        TASK_STORE_New.create_task(
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
    t = threading.Thread(target=run_task, args=(TASK_STORE_New, task_id, title, args), daemon=True)
    # # ---
    t.start()

    return redirect(url_for("index", task_id=task_id))


@app.get("/index2")
def index2():
    task_id = request.args.get("task_id")
    task = TASK_STORE_New.get_task(task_id) if task_id else None

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found")

    error_code = request.args.get("error")
    error_message = None
    if error_code == "task-active":
        error_message = "A task for this title is already in progress."

    return render_template(
        "index2.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}),
        error_message=error_message,
    )


def _format_timestamp(value: datetime | str | None) -> tuple[str, str]:
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


@app.get("/tasks")
def tasks():
    status_filter = request.args.get("status")
    tasks = TASK_STORE_New.list_tasks(status=status_filter, order_by="created_at", descending=True)

    formatted_tasks = []
    status_values = set()
    for task in tasks:
        results = task.get("results") or {}
        injects = results.get("injects_result") or {}

        created_display, created_sort = _format_timestamp(task.get("created_at"))
        updated_display, updated_sort = _format_timestamp(task.get("updated_at"))

        if task.get("status"):
            status_values.add(task.get("status"))

        formatted_tasks.append({
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
        })

    available_statuses = sorted(status_values)

    return render_template(
        "tasks.html",
        tasks=formatted_tasks,
        status_filter=status_filter,
        available_statuses=available_statuses,
    )


@app.get("/status/<task_id>")
def status(task_id: str):
    task = TASK_STORE_New.get_task(task_id)
    if not task:
        logger.debug(f"Task {task_id} not found")
        return jsonify({"error": "not-found"}), 404
    return jsonify(task)


if __name__ == "__main__":
    debug = "debug" in sys.argv
    app.run(debug=debug)
