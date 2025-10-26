"""Admin-only routes for monitoring application tasks."""

from __future__ import annotations

from collections import Counter

from flask import Blueprint, abort, redirect, render_template, url_for

from ...config import settings
from ...users.current import current_user
from ..tasks.routes import (
    TASKS_LOCK,
    _task_store,
    format_task,
    format_task_message,
)

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")


@bp_admin.get("/")
@bp_admin.get("")
def dashboard():
    """Render the admin dashboard with summarized task information."""

    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if user.username not in settings.admins:
        abort(403)

    with TASKS_LOCK:
        db_tasks = _task_store().list_tasks(
            order_by="created_at",
            descending=True,
        )

    formatted = [format_task(task) for task in db_tasks]
    formatted = format_task_message(formatted)

    status_counts = Counter(task.get("status", "Unknown") for task in formatted)
    active_statuses = {"Running", "Pending"}
    active_tasks = sum(1 for task in formatted if task.get("status") in active_statuses)

    return render_template(
        "admin_dashboard.html",
        current_user=user,
        tasks=formatted,
        total_tasks=len(formatted),
        active_tasks=active_tasks,
        status_counts=status_counts,
    )
