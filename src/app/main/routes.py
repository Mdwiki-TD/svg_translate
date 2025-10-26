"""
!
"""

from __future__ import annotations

import logging

from flask import (
    Blueprint,
    render_template,
    request,
)
from ..routes_utils import get_error_message

bp_main = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@bp_main.get("/")
def index():
    error_message = get_error_message(request.args.get("error"))

    return render_template(
        "index.html",
        form={},
        error_message=error_message,
    )


__all__ = [
    "bp_main"
]
