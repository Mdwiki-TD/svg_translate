"""Admin-only routes for managing coordinator access."""

from __future__ import annotations

from collections import Counter

from flask import (
    Blueprint,
    render_template,
)
from ...tasks.routes import (
    _task_store,
    format_task,
    format_task_message,
    TASKS_LOCK,
)
from ..admin_required import admin_required


def _recent_routes():
    """Render the admin dashboard with summarized task information."""

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
        "admins/admin.html",
        # current_user=user,
        tasks=formatted,
        total_tasks=len(formatted),
        active_tasks=active_tasks,
        status_counts=status_counts,
    )


class Recent:
    def __init__(self, bp_admin: Blueprint):

        @bp_admin.get("/recent")
        @admin_required
        def recent_routes():
            return _recent_routes()
