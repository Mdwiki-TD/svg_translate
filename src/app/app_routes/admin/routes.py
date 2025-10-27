"""Admin-only routes for managing coordinator access."""

from __future__ import annotations
from flask import (
    Blueprint,
    url_for,
    redirect,
    request,
)

# from ...users.current import current_user
from .admin_required import admin_required
from .admin_routes.coordinators import Coordinators
from .admin_routes.recent import Recent
from .sidebar import create_side

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")


@bp_admin.app_context_processor
def inject_sidebar():
    path_parts = request.path.strip("/").split("/")
    ty = path_parts[1] if len(path_parts) > 1 else ""
    sidebar_html = create_side(ty=ty)
    return dict(sidebar=sidebar_html)


@bp_admin.get("/")
@admin_required
def admin_dashboard():
    return redirect(url_for("admin.recent_routes"))
    # user = current_user()
    # return render_template( "admins.html", current_user=user, )


Coordinators(bp_admin)

Recent(bp_admin)
