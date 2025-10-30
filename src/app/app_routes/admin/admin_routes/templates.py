"""
TODO:
CSRF protection is missing on state‑changing POST endpoints.

Admin writes (add/toggle/delete) should be CSRF‑protected. The three POST forms in templates/admins/templates.html lack CSRF tokens, and create_app() does not initialize CSRFProtect.

Enable Flask‑WTF CSRFProtect globally in create_app() and add {{ csrf_token() }} in all three forms.
Or implement a custom double‑submit header/token check for POST requests under /admin.
Affected forms in templates/admins/templates.html:

"""

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
from ....app_routes.templates import template_service
from ..admin_required import admin_required

logger = logging.getLogger(__name__)


def _templates_dashboard():
    """Render the template management dashboard."""

    user = current_user()
    templates = template_service.list_templates()
    total = len(templates)
    active = sum(1 for coord in templates if coord.is_active)

    return render_template(
        "admins/templates.html",
        current_user=user,
        templates=templates,
        total_templates=total,
        active_templates=active,
        inactive_templates=total - active,
    )


def _add_template() -> ResponseReturnValue:
    """Create a new template from the submitted title."""

    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required to add a template.", "danger")
        return redirect(url_for("admin.templates_dashboard"))

    try:
        record = template_service.add_template(title)
    except ValueError as exc:
        flash(str(exc), "warning")
    except LookupError as exc:
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        logger.exception("Unable to add template.")
        flash("Unable to add template. Please try again.", "danger")
    else:
        flash(f"Template '{record.title}' added.", "success")

    return redirect(url_for("admin.templates_dashboard"))


def _update_template_active(template_id: int) -> ResponseReturnValue:
    """Toggle the active flag for a template."""

    desired = request.form.get("active", "0") == "1"
    try:
        record = template_service.set_template_active(template_id, desired)
    except LookupError as exc:
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        flash("Unable to update template status. Please try again.", "danger")
    else:
        state = "activated" if record.is_active else "deactivated"
        flash(f"Template '{record.title}' {state}.", "success")

    return redirect(url_for("admin.templates_dashboard"))


def _delete_template(template_id: int) -> ResponseReturnValue:
    """Remove a template entirely."""

    try:
        record = template_service.delete_template(template_id)
    except LookupError as exc:
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        flash("Unable to delete template. Please try again.", "danger")
    else:
        flash(f"Template '{record.title}' removed.", "success")

    return redirect(url_for("admin.templates_dashboard"))


class Templates:
    def __init__(self, bp_admin: Blueprint):

        @bp_admin.get("/templates")
        @admin_required
        def templates_dashboard():
            return _templates_dashboard()

        @bp_admin.post("/templates/add")
        @admin_required
        def add_template() -> ResponseReturnValue:
            return _add_template()

        @bp_admin.post("/templates/<int:template_id>/active")
        @admin_required
        def update_template_active(template_id: int) -> ResponseReturnValue:
            return _update_template_active(template_id)

        @bp_admin.post("/templates/<int:template_id>/delete")
        @admin_required
        def delete_template(template_id: int) -> ResponseReturnValue:
            return _delete_template(template_id)
