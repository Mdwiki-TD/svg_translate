"""Main Flask views for the SVG Translate web application."""

from __future__ import annotations

import threading
import uuid
from collections import namedtuple
from datetime import datetime
from typing import Any, Dict, List

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from svg_config import db_data

try:  # pragma: no cover - maintain compatibility with both package layouts
    from svg_translate.log import config_logger, logger
except ImportError:  # pragma: no cover
    from src.svg_translate.log import config_logger, logger  # type: ignore[no-redef]

from web.auth import oauth_required
from web.db.task_store_pymysql import TaskAlreadyExistsError, TaskStorePyMysql
from web.web_run_task import run_task

config_logger("DEBUG")

bp = Blueprint("main", __name__)


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
    return current_app.extensions.setdefault(
        "task_store", TaskStorePyMysql(current_app.config["DB_DATA"])
    )


def _task_lock() -> threading.Lock:
    return current_app.extensions.setdefault("task_lock", threading.Lock())


def parse_args(request_form) -> Any:
    Args = namedtuple("Args", ["titles_limit", "overwrite", "upload", "ignore_existing_task"])
    upload = bool(request_form.get("upload"))
    return Args(
        titles_limit=request_form.get("titles_limit", 1000, type=int),
        overwrite=bool(request_form.get("overwrite")),
        ignore_existing_task=bool(request_form.get("ignore_existing_task")),
        upload=upload
    )


def _format_timestamp(value: datetime | str | None) -> tuple[str, str]:
    if not value:
        return "", ""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = None
        for fmt in (None, "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.fromisoformat(value) if fmt is None else datetime.strptime(value, fmt)
                break
            except (TypeError, ValueError):
                continue
        if dt is None:
            return value, value
    return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.isoformat()


def _format_task(task: dict) -> dict:
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
    ordered = [
        (name, data)
        for name, data in stages.items()
        if isinstance(data, dict)
    ]
    ordered.sort(key=lambda item: item[1].get("number", 0))
    return ordered


@bp.get("/healthz")
def healthcheck():
    return {"status": "ok"}, 200


@bp.get("/")
def index():
    error_message = get_error_message(request.args.get("error"))
    return render_template("index.html", form={}, error_message=error_message)


@bp.get("/task1")
def task1():
    task_id = request.args.get("task_id")
    task = _task_store().get_task(task_id) if task_id else None
    if not task:
        task = {"error": "not-found"}
        logger.debug("Task %s not found!!", task_id)

    error_message = get_error_message(request.args.get("error"))

    return render_template(
        "task1.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}) if isinstance(task, dict) else {},
        error_message=error_message,
    )


@bp.get("/task2")
def task2():
    task_id = request.args.get("task_id")
    title = request.args.get("title")
    task = _task_store().get_task(task_id) if task_id else None
    if not task:
        task = {"error": "not-found"}
        logger.debug("Task %s not found!!", task_id)

    error_message = get_error_message(request.args.get("error"))

    stages = _order_stages(task.get("stages") if isinstance(task, dict) else None)

    return render_template(
        "task2.html",
        task_id=task_id,
        title=title or task.get("title", "") if isinstance(task, dict) else "",
        task=task,
        stages=stages,
        error_message=error_message,
    )


@bp.get("/tasks")
def tasks():
    status_filter = request.args.get("status")

    with _task_lock():
        db_tasks = _task_store().list_tasks(
            status=status_filter,
            order_by="created_at",
            descending=True,
        )

    formatted = [_format_task(task) for task in db_tasks]
    available_statuses = sorted(
        {task.get("status") for task in db_tasks if task.get("status")}
    )

    return render_template(
        "tasks.html",
        tasks=formatted,
        status_filter=status_filter,
        available_statuses=available_statuses,
    )


@bp.get("/status/<task_id>")
def status(task_id: str):
    if not task_id:
        logger.error("No task_id provided in status request.")
        return jsonify({"error": "no-task-id"}), 400

    task = _task_store().get_task(task_id)
    if not task:
        logger.debug("Task %s not found", task_id)
        return jsonify({"error": "not-found"}), 404

    return jsonify(task)


@bp.post("/start")
# @oauth_required
def start():
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("main.index"))

    task_id = uuid.uuid4().hex

    args = parse_args(request.form)

    with _task_lock():
        if not args.ignore_existing_task:
            existing_task = _task_store().get_active_task_by_title(title)
            if existing_task:
                logger.debug("Task for title '%s' already exists: %s.", title, existing_task["id"])
                return redirect(
                    url_for("main.task1", task_id=existing_task["id"], title=title, error="task-active")
                )

        try:
            _task_store().create_task(
                task_id,
                title,
                form=request.form.to_dict(flat=True),
            )
        except TaskAlreadyExistsError as exc:
            existing = exc.task
            return redirect(
                url_for("main.task1", task_id=existing["id"], title=title, error="task-active")
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to create task", exc_info=exc)
            return redirect(url_for("main.index", title=title, error="task-create-failed"))

    credentials = getattr(g, "oauth_credentials", {}) or {}
    auth_payload = {
        "consumer_key": credentials.get("consumer_key"),
        "consumer_secret": credentials.get("consumer_secret"),
        "access_token": credentials.get("access_token"),
        "access_secret": credentials.get("access_secret"),
    }

    thread = threading.Thread(
        target=current_app.extensions.get("run_task", run_task),
        args=(dict(current_app.config["DB_DATA"]), task_id, title, args, auth_payload),
        name=f"task-runner-{task_id[:8]}",
        daemon=True,
    )
    thread.start()

    return redirect(url_for("main.task1", title=title, task_id=task_id))


def init_app(app) -> None:
    if "DB_DATA" not in app.config:
        app.config["DB_DATA"] = dict(db_data)
    app.extensions.setdefault("run_task", run_task)
    app.register_blueprint(bp)


__all__ = ["bp", "init_app", "parse_args"]
