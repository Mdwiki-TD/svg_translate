"""Main Flask views for the SVG Translate web application."""

from __future__ import annotations

import threading
import logging
from typing import Any, Dict

from ..config import settings
from . import web_run_task

CANCEL_EVENTS: Dict[str, threading.Event] = {}
CANCEL_EVENTS_LOCK = threading.Lock()
# The use of a global dictionary CANCEL_EVENTS with a threading.Lock ties the cancellation mechanism to a single-process, multi-threaded server model. This approach will not work correctly in a multi-process environment (e.g., when using Gunicorn with multiple worker processes), as each process would have its own independent copy of CANCEL_EVENTS. For a more scalable and robust solution, consider using a shared external store like Redis or a database to manage cancellation state across processes.

logger = logging.getLogger(__name__)


def _register_cancel_event(task_id: str, cancel_event: threading.Event) -> None:
    with CANCEL_EVENTS_LOCK:
        CANCEL_EVENTS[task_id] = cancel_event


def _pop_cancel_event(task_id: str) -> threading.Event | None:
    with CANCEL_EVENTS_LOCK:
        return CANCEL_EVENTS.pop(task_id, None)


def get_cancel_event(task_id: str) -> threading.Event | None:
    with CANCEL_EVENTS_LOCK:
        return CANCEL_EVENTS.get(task_id)


def launch_task_thread(
    task_id: str,
    title: str,
    args: Any,
    user_payload: Dict[str, Any],
) -> None:
    cancel_event = threading.Event()
    _register_cancel_event(task_id, cancel_event)

    def _runner() -> None:
        try:
            web_run_task.run_task(
                settings.db_data,
                task_id,
                title,
                args,
                user_payload,
                cancel_event=cancel_event,
            )
        finally:
            _pop_cancel_event(task_id)

    t = threading.Thread(
        target=_runner,
        name=f"task-runner-{task_id[:8]}",
        daemon=True,
    )
    t.start()


__all__ = [
    "get_cancel_event",
    "launch_task_thread",
]
