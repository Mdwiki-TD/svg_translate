#
from __future__ import annotations

from collections import namedtuple
import logging
from typing import Any
from ..svg_config import DISABLE_UPLOADS

logger = logging.getLogger(__name__)


def parse_args(request_form: Any) -> Any:
    Args = namedtuple(
        "Args",
        [
            "titles_limit",
            "overwrite",
            "upload",
            "ignore_existing_task",
            "manual_main_title",
        ],
    )
    # ---
    upload = False
    # ---
    if DISABLE_UPLOADS != "1":
        upload = bool(request_form.get("upload"))
    # ---
    manual_main_title = request_form.get("manual_main_title", "").strip()
    if manual_main_title.lower().startswith("file:"):
        manual_main_title = manual_main_title.split(":", 1)[1].strip()

    if not manual_main_title:
        manual_main_title = None

    return Args(
        titles_limit=request_form.get("titles_limit", 1000, type=int),
        overwrite=bool(request_form.get("overwrite")),
        ignore_existing_task=bool(request_form.get("ignore_existing_task")),
        upload=upload,
        manual_main_title=manual_main_title,
    )
