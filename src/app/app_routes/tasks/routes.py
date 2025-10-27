"""Main Flask views for the SVG Translate web application."""

from __future__ import annotations

import threading
import uuid
import logging
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from ...config import settings
from ...db.task_store_pymysql import TaskAlreadyExistsError, TaskStorePyMysql
from ...users.current import current_user, oauth_required

from ...routes_utils import load_auth_payload, get_error_message, format_task, order_stages
from .args_utils import parse_args

from ...threads.task_threads import launch_task_thread

TASK_STORE: TaskStorePyMysql | None = None
TASKS_LOCK = threading.Lock()

bp_tasks = Blueprint("tasks", __name__)
logger = logging.getLogger(__name__)


def format_task_message(formatted):
    for v in formatted:
        if v.get('stages'):
            for s in v['stages']:
                v['stages'][s]['message'] = '<br>'.join(v['stages'][s]['message'].split(','))
    return formatted


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


@bp_tasks.get("/task1")
@bp_tasks.get("/task1/<task_id>")
def task1(task_id: str | None = None):
    if not task_id:
        return redirect(url_for("main.index", error="no-task-id"))

    task = _task_store().get_task(task_id)

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    title = request.args.get("title")
    error_message = get_error_message(request.args.get("error"))

    current_user_obj = current_user()
    return render_template(
        "task1.html",
        task_id=task_id,
        current_user=current_user_obj,
        title=title or task.get("title", "") if isinstance(task, dict) else "",
        task=task,
        form=task.get("form", {}),
        error_message=error_message,
    )


@bp_tasks.get("/task2")
def task2():
    task_id = request.args.get("task_id")

    if not task_id:
        return redirect(url_for("main.index", error="no-task-id"))

    task = _task_store().get_task(task_id)

    if not task:
        task = {"error": "not-found"}
        logger.debug(f"Task {task_id} not found!!")

    title = request.args.get("title")
    error_message = get_error_message(request.args.get("error"))

    stages = order_stages(task.get("stages") if isinstance(task, dict) else None)

    current_user_obj = current_user()
    return render_template(
        "task2.html",
        task_id=task_id,
        current_user=current_user_obj,
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

    launch_task_thread(task_id, title, args, auth_payload)

    return redirect(url_for("tasks.task1", title=title, task_id=task_id))


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


@bp_tasks.get("/tasks")
@bp_tasks.get("/tasks/<user>")
def tasks(user: str | None = None):
    """
    Render the task listing page with formatted task metadata and available status filters.

    Retrieve tasks from the global task store, optionally filter by status, and produce a list of task dictionaries with selected fields and display/sortable timestamp values. Also collect the distinct task statuses found and pass the tasks, the current status filter, and the sorted available statuses to the "tasks.html" template.

    Returns:
        A Flask response object rendering "tasks.html" with the context keys `tasks`, and `available_statuses`.
    """

    # Get username from query parameter, default to current user
    # user = request.args.get("user", "")
    current_user_obj = current_user()

    with TASKS_LOCK:
        db_tasks = _task_store().list_tasks(
            username=user,
            order_by="created_at",
            descending=True,
        )

    formatted = [format_task(task) for task in db_tasks]
    formatted = format_task_message(formatted)

    available_statuses = sorted(
        {
            task.get("status", "") for task in db_tasks if task.get("status")
        }
    )

    # Determine if viewing own tasks or another user's tasks
    is_own_tasks = current_user_obj and user == current_user_obj.username

    return render_template(
        "tasks.html",
        tasks=formatted,
        available_statuses=available_statuses,
        current_user=current_user_obj,
        tasks_user=user,
        is_own_tasks=is_own_tasks,
        user_specific=True,
    )
