"""
Defines the main routes for the application, such as the homepage.
"""

from __future__ import annotations

import logging

from flask import (
    Blueprint,
    flash,
    render_template,
    request,
    send_from_directory,
)
from ...routes_utils import get_error_message
from ...users.current import current_user

bp_main = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@bp_main.get("/")
def index():
    current_user_obj = current_user()
    error_message = get_error_message(request.args.get("error"))
    if error_message:
        logger.warning(f"Error message: {error_message}")
        flash(error_message, "warning")

    return render_template(
        "index.html",
        form={},
        current_user=current_user_obj,
    )


@bp_main.get("/favicon.ico")
def favicon():
    return send_from_directory(
        "static", "favicon.ico", mimetype="image/x-icon"
    )


__all__ = [
    "bp_main"
]
