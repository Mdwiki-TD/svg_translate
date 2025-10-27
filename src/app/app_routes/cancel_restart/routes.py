"""Main Flask views for the SVG Translate web application."""

from __future__ import annotations

import threading
import uuid
import logging
from functools import wraps
from typing import Any, Dict, Callable

from flask import (
    Blueprint,
    jsonify,
)
from werkzeug.datastructures import MultiDict

from ...config import settings
from ...db.task_store_pymysql import TaskStorePyMysql
from ...db import TaskAlreadyExistsError
from ...users.current import current_user
from ..tasks.args_utils import parse_args

from ...threads.task_threads import launch_task_thread, get_cancel_event

TASK_STORE: TaskStorePyMysql | None = None
TASKS_LOCK = threading.Lock()

bp_tasks_managers = Blueprint("tasks_managers", __name__)
logger = logging.getLogger(__name__)


def _task_store() -> TaskStorePyMysql:
    global TASK_STORE
    if TASK_STORE is None:
        TASK_STORE = TaskStorePyMysql(settings.db_data)
    return TASK_STORE


def login_required_json(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that redirects anonymous users to the index page."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():  # and not getattr(g, "is_authenticated", False)
            # return redirect(url_for("main.index", error="login-required"))
            return jsonify({"error": "login-required"})
        return fn(*args, **kwargs)

    return wrapper


@bp_tasks_managers.post("/tasks/<task_id>/cancel")
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

    if task_username != user.username and user.username not in settings.admins:
        logger.error(
            "Cancel requested for task %s by user %s, but task is owned by %s",
            task_id,
            user.username,
            task_username,
        )
        return jsonify({"error": "You don't own this task"}), 403

    cancel_event = get_cancel_event(task_id)
    if cancel_event:
        cancel_event.set()

    store.update_status(task_id, "Cancelled")

    return jsonify({"task_id": task_id, "status": "Cancelled"})


@bp_tasks_managers.post("/tasks/<task_id>/restart")
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

    launch_task_thread(new_task_id, title, args, user_payload)

    return jsonify({"task_id": new_task_id, "status": "Running"})


__all__ = [
    "bp_tasks_managers"
]
