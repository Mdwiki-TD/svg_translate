"""Admin-only routes for managing coordinator access."""

from __future__ import annotations
import logging
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue

from ....users.current import current_user
from ....users import admin_service
from ..admin_required import admin_required

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")

logger = logging.getLogger(__name__)


def _coordinators_dashboard():
    """Render the coordinator management dashboard."""

    user = current_user()
    coordinators = admin_service.list_coordinators()
    total = len(coordinators)
    active = sum(1 for coord in coordinators if coord.is_active)

    return render_template(
        "admins/coordinators.html",
        current_user=user,
        coordinators=coordinators,
        total_coordinators=total,
        active_coordinators=active,
        inactive_coordinators=total - active,
    )


def _add_coordinator() -> ResponseReturnValue:
    """Create a new coordinator from the submitted username."""

    username = request.form.get("username", "").strip()
    if not username:
        flash("Username is required to add a coordinator.", "danger")
        return redirect(url_for("admin.coordinators_dashboard"))

    try:
        record = admin_service.add_coordinator(username)
    except ValueError as exc:
        flash(str(exc), "warning")
    except LookupError as exc:
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        logger.exception("Unable to add coordinator.")
        flash("Unable to add coordinator. Please try again.", "danger")
    else:
        flash(f"Coordinator '{record.username}' added.", "success")

    return redirect(url_for("admin.coordinators_dashboard"))


def _update_coordinator_active(coordinator_id: int) -> ResponseReturnValue:
    """Toggle the active flag for a coordinator."""

    desired = request.form.get("active", "0") == "1"
    try:
        record = admin_service.set_coordinator_active(coordinator_id, desired)
    except LookupError as exc:
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        flash("Unable to update coordinator status. Please try again.", "danger")
    else:
        state = "activated" if record.is_active else "deactivated"
        flash(f"Coordinator '{record.username}' {state}.", "success")

    return redirect(url_for("admin.coordinators_dashboard"))


def _delete_coordinator(coordinator_id: int) -> ResponseReturnValue:
    """Remove a coordinator entirely."""

    try:
        record = admin_service.delete_coordinator(coordinator_id)
    except LookupError as exc:
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        flash("Unable to delete coordinator. Please try again.", "danger")
    else:
        flash(f"Coordinator '{record.username}' removed.", "success")

    return redirect(url_for("admin.coordinators_dashboard"))


class Coordinators:
    def __init__(self, bp_admin: Blueprint):

        @bp_admin.get("/coordinators")
        @admin_required
        def coordinators_dashboard():
            return _coordinators_dashboard()

        @bp_admin.post("/coordinators/add")
        @admin_required
        def add_coordinator() -> ResponseReturnValue:
            return _add_coordinator()

        @bp_admin.post("/coordinators/<int:coordinator_id>/active")
        @admin_required
        def update_coordinator_active(coordinator_id: int) -> ResponseReturnValue:
            return _update_coordinator_active(coordinator_id)

        @bp_admin.post("/coordinators/<int:coordinator_id>/delete")
        @admin_required
        def delete_coordinator(coordinator_id: int) -> ResponseReturnValue:
            return _delete_coordinator(coordinator_id)
