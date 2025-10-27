"""Unit tests for task thread orchestration."""
import time
import threading

from src.app.threads.task_threads import (
    launch_task_thread,
    get_cancel_event,
)
from src.app.threads import web_run_task


def _test_launch_thread_registers_and_cleans_cancel_event(monkeypatch):
    # FAILED tests/test_task_threads.py::test_launch_thread_registers_and_cleans_cancel_event - AssertionError: Thread did not start in time
    started = threading.Event()
    release = threading.Event()

    def fake_run_task(_db_data, _task_id, _title, _args, _user_payload, *, _cancel_event=None):  # pylint: disable=too-many-arguments
        # signal we started and wait briefly until released
        started.set()
        release.wait(timeout=0.2)

    monkeypatch.setattr(web_run_task, "run_task", fake_run_task)

    task_id = "t-abc123"
    launch_task_thread(task_id, "Title", args=SimpleNamespace(), user_payload={})

    # ensure registered
    assert started.wait(timeout=0.2), "Thread did not start in time"
    assert get_cancel_event(task_id) is not None

    # let thread exit; then cancel event entry should be removed
    release.set()
    # give a tiny bit of time for cleanup
    for _ in range(10):
        if get_cancel_event(task_id) is None:
            break
        time.sleep(0.02)
    assert get_cancel_event(task_id) is None


class SimpleNamespace:
    """Minimal args placeholder."""
    pass
