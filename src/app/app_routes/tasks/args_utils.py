#
from __future__ import annotations
from dataclasses import dataclass

import logging
from ...config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Args:
    titles_limit: int
    overwrite: bool
    upload: bool
    ignore_existing_task: bool
    manual_main_title: str | None


def parse_args(request_form) -> Args:
    upload = False

    if settings.disable_uploads != "1":
        upload = bool(request_form.get("upload"))

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
