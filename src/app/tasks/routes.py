"""Main Flask views for the SVG Translate web application."""

from __future__ import annotations

import threading
import uuid
import logging
from functools import wraps
from typing import Any, Dict, Callable

from flask import (
    Blueprint,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.datastructures import MultiDict

from ..config import settings
from ..web.web_run_task import run_task
from ..db.task_store_pymysql import TaskAlreadyExistsError, TaskStorePyMysql
from ..users.current import current_user, oauth_required

from ..routes_utils import load_auth_payload, get_error_message, _format_task, _order_stages
from .args_utils import parse_args

TASK_STORE: TaskStorePyMysql | None = None
TASKS_LOCK = threading.Lock()

CANCEL_EVENTS: Dict[str, threading.Event] = {}
CANCEL_EVENTS_LOCK = threading.Lock()
# The use of a global dictionary CANCEL_EVENTS with a threading.Lock ties the cancellation mechanism to a single-process, multi-threaded server model. This approach will not work correctly in a multi-process environment (e.g., when using Gunicorn with multiple worker processes), as each process would have its own independent copy of CANCEL_EVENTS. For a more scalable and robust solution, consider using a shared external store like Redis or a database to manage cancellation state across processes.

bp_tasks = Blueprint("tasks", __name__)
logger = logging.getLogger(__name__)


def _task_store() -> TaskStorePyMysql:
    global TASK_STORE
    if TASK_STORE is None:
        TASK_STORE = TaskStorePyMysql(settings.db_data)
    return TASK_STORE


def close_task_store() -> None:
    """Close the cached :class:`TaskStorePyMysql` instance if present."""
    global TASK_STORE
    if TASK_STORE is not None:
        TASK_STORE.close()


def _register_cancel_event(task_id: str, cancel_event: threading.Event) -> None:
    with CANCEL_EVENTS_LOCK:
        CANCEL_EVENTS[task_id] = cancel_event


def _pop_cancel_event(task_id: str) -> threading.Event | None:
    with CANCEL_EVENTS_LOCK:
        return CANCEL_EVENTS.pop(task_id, None)


def _get_cancel_event(task_id: str) -> threading.Event | None:
    with CANCEL_EVENTS_LOCK:
        return CANCEL_EVENTS.get(task_id)


def _launch_task_thread(
    task_id: str,
    title: str,
    args: Any,
    user_payload: Dict[str, Any],
) -> None:
    cancel_event = threading.Event()
    _register_cancel_event(task_id, cancel_event)

    def _runner() -> None:
        try:
            run_task(
                settings.db_data,
                task_id,
                title,
                args,
                user_payload,
                cancel_event=cancel_event,
            )
        finally:
            _pop_cancel_event(task_id)

    t = threading.Thread(
        target=_runner,
        name=f"task-runner-{task_id[:8]}",
        daemon=True,
    )
    t.start()


@bp_tasks.get("/task1")
def task1():
    task_id = request.args.get("task_id")
    task = None
    if task_id:
        task = _task_store().get_task(task_id)

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    error_message = get_error_message(request.args.get("error"))

    return render_template(
        "task1.html",
        task_id=task_id,
        task=task,
        form=task.get("form", {}) if isinstance(task, dict) else {},
        error_message=error_message,
    )


@bp_tasks.get("/task2")
def task2():
    task_id = request.args.get("task_id")
    title = request.args.get("title")
    task = None
    if task_id:
        task = _task_store().get_task(task_id)

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    error_message = get_error_message(request.args.get("error"))

    stages = _order_stages(task.get("stages") if isinstance(task, dict) else None)

    return render_template(
        "task2.html",
        task_id=task_id,
        title=title or task.get("title", "") if isinstance(task, dict) else "",
        task=task,
        stages=stages,
        form=task.get("form", {}),
        error_message=error_message,
    )


@bp_tasks.post("/")
@oauth_required
def start():
    user = current_user()
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(url_for("main.index"))

    task_id = uuid.uuid4().hex

    store = _task_store()

    args = parse_args(request.form)

    with TASKS_LOCK:
        logger.info(f"ignore_existing_task: {args.ignore_existing_task}")
        if not args.ignore_existing_task:
            existing_task = store.get_active_task_by_title(title)
            if existing_task:
                logger.debug(f"Task for title '{title}' already exists: {existing_task['id']}.")
                return redirect(
                    url_for("tasks.task1", task_id=existing_task["id"], title=title, error="task-active")
                )

        try:
            store.create_task(
                task_id,
                title,
                username=(user.username if user else ""),
                form=request.form.to_dict(flat=True)
            )
        except TaskAlreadyExistsError as exc:
            existing = exc.task
            logger.debug("Task creation for %s blocked by existing task %s", task_id, existing.get("id"))
            return redirect(url_for("tasks.task1", task_id=existing["id"], title=title, error="task-active"))
        except Exception:
            logger.exception("Failed to create task")
            return redirect(url_for("main.index", title=title, error="task-create-failed"))

    auth_payload = load_auth_payload(user)

    _launch_task_thread(task_id, title, args, auth_payload)

    return redirect(url_for("tasks.task1", title=title, task_id=task_id))


@bp_tasks.get("/tasks")
def tasks():
    """
    Render the task listing page with formatted task metadata and available status filters.

    Retrieve tasks from the global task store, optionally filter by status, and produce a list of task dictionaries with selected fields and display/sortable timestamp values. Also collect the distinct task statuses found and pass the tasks, the current status filter, and the sorted available statuses to the "tasks.html" template.

    Returns:
        A Flask response object rendering "tasks.html" with the context keys `tasks`, `status_filter`, and `available_statuses`.
    """
    status_filter = request.args.get("status")

    with TASKS_LOCK:
        db_tasks = _task_store().list_tasks(
            status=status_filter,
            order_by="created_at",
            descending=True,
        )

    formatted = [_format_task(task) for task in db_tasks]
    available_statuses = sorted(
        {
            task.get("status", "") for task in db_tasks  # if task.get("status")
        }
    )

    return render_template(
        "tasks.html",
        tasks=formatted,
        status_filter=status_filter,
        available_statuses=available_statuses,
    )


@bp_tasks.get("/status/<task_id>")
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

    task = _task_store().get_task(task_id)
    if not task:
        logger.debug(f"Task {task_id} not found")
        return jsonify({"error": "not-found"}), 404

    return jsonify(task)


def login_required_json(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that redirects anonymous users to the index page."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():  # and not getattr(g, "is_authenticated", False)
            # return redirect(url_for("main.index", error="login-required"))
            return jsonify({"error": "login-required"})
        return fn(*args, **kwargs)

    return wrapper


@bp_tasks.post("/tasks/<task_id>/cancel")
@login_required_json
def cancel(task_id: str):
    if not task_id:
        return jsonify({"error": "no-task-id"}), 400

    store = _task_store()
    task = store.get_task(task_id)
    if not task:
        logger.debug("Cancel requested for missing task %s", task_id)
        return jsonify({"error": "not-found"}), 404

    if task.get("status") in ("Completed", "Failed", "Cancelled"):
        return jsonify({"task_id": task_id, "status": task.get("status")})

    user = current_user()
    if not user:
        logger.error("Cancel requested without authenticated user for task %s", task_id)
        return jsonify({"error": "You are not authenticated"}), 401

    task_username = task.get("username", "")

    if task_username != user.username:
        logger.error(
            "Cancel requested for task %s by user %s, but task is owned by %s",
            task_id,
            user.username,
            task_username,
        )
        return jsonify({"error": "You don't own this task"}), 403

    cancel_event = _get_cancel_event(task_id)
    if cancel_event:
        cancel_event.set()

    store.update_status(task_id, "Cancelled")

    return jsonify({"task_id": task_id, "status": "Cancelled"})


@bp_tasks.post("/tasks/<task_id>/restart")
@login_required_json
def restart(task_id: str):
    if not task_id:
        return jsonify({"error": "no-task-id"}), 400

    store = _task_store()
    task = store.get_task(task_id)
    if not task:
        logger.debug("Restart requested for missing task %s", task_id)
        return jsonify({"error": "not-found"}), 404

    title = task.get("title")
    if not title:
        logger.error("Task %s has no title to restart", task_id)
        return jsonify({"error": "no-title"}), 400

    user = current_user()
    if not user:
        logger.error("Restart requested without authenticated user for task %s", task_id)
        return jsonify({"error": "not-authenticated"}), 401

    user_payload: Dict[str, Any] = {
        "id": user.user_id,
        "username": user.username,
        "access_token": user.access_token,
        "access_secret": user.access_secret,
    }

    stored_form = dict(task.get("form") or {})
    request_form = MultiDict(stored_form.items()) if stored_form else MultiDict()
    args = parse_args(request_form)

    new_task_id = uuid.uuid4().hex

    with TASKS_LOCK:
        try:
            store.create_task(
                new_task_id,
                title,
                username=user.username,
                form=stored_form,
            )
        except TaskAlreadyExistsError as exc:
            existing = exc.task
            logger.debug("Restart for %s blocked by existing task %s", task_id, existing.get("id"))
            return (
                jsonify({"error": "task-active", "task_id": existing.get("id")}),
                409,
            )
        except Exception:
            logger.exception("Failed to restart task %s", task_id)
            return jsonify({"error": "task-create-failed"}), 500

    _launch_task_thread(new_task_id, title, args, user_payload)

    return jsonify({"task_id": new_task_id, "status": "Running"})
