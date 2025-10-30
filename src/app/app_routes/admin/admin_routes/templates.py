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
from .... import template_service
from ..admin_required import admin_required

logger = logging.getLogger(__name__)


def _templates_dashboard():
    """Render the template management dashboard."""

    user = current_user()
    templates = template_service.list_templates()
    total = len(templates)

    return render_template(
        "admins/templates.html",
        current_user=user,
        templates=templates,
        total_templates=total,
    )


def _add_template() -> ResponseReturnValue:
    """Create a new template from the submitted title."""

    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required to add a template.", "danger")
        return redirect(url_for("admin.templates_dashboard"))

    main_file = request.form.get("main_file", "").strip()
    try:
        record = template_service.add_template(title, main_file)
    except ValueError as exc:
        logger.exception("Unable to add template.")
        flash(str(exc), "warning")
    except LookupError as exc:
        logger.exception("Unable to add template.")
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        logger.exception("Unable to add template.")
        flash("Unable to add template. Please try again.", "danger")
    else:
        flash(f"Template '{record.title}' added.", "success")

    return redirect(url_for("admin.templates_dashboard"))


def _update_template() -> ResponseReturnValue:
    """Update main_file for a template."""
    template_id = request.form.get("id", 0).strip()
    template_id = int(template_id)

    if not template_id:
        flash("Template ID is required to update a template.", "danger")
        return redirect(url_for("admin.templates_dashboard"))

    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required to add a template.", "danger")
        return redirect(url_for("admin.templates_dashboard"))

    main_file = request.form.get("main_file", "").strip()

    try:
        record = template_service.update_template(template_id, title, main_file)
    except LookupError as exc:
        logger.exception("Unable to Update template.")
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        logger.exception("Unable to update template.")
        flash("Unable to update template main file. Please try again.", "danger")
    else:
        flash(f"Template '{record.title}' main file: {main_file} updated.", "success")

    return redirect(url_for("admin.templates_dashboard"))


def _delete_template(template_id: int) -> ResponseReturnValue:
    """Remove a template entirely."""

    try:
        record = template_service.delete_template(template_id)
    except LookupError as exc:
        logger.exception("Unable to delete template.")
        flash(str(exc), "warning")
    except Exception:  # pragma: no cover - defensive guard
        logger.exception("Unable to delete template.")
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

        @bp_admin.post("/templates/update")
        @admin_required
        def update_template() -> ResponseReturnValue:
            return _update_template()

        @bp_admin.post("/templates/<int:template_id>/delete")
        @admin_required
        def delete_template(template_id: int) -> ResponseReturnValue:
            return _delete_template(template_id)
