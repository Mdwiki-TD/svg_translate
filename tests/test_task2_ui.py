import re

import pytest

from src.app import create_app
from src.app.tasks import routes as task_routes


class DummyStore:
    def __init__(self, task):
        self._task = task

    def get_task(self, task_id):  # pragma: no cover - trivial
        return self._task


@pytest.fixture
def app_factory(monkeypatch):
    def _factory(task):
        app = create_app()
        app.config["TESTING"] = True
        monkeypatch.setattr(task_routes, "TASK_STORE", None)
        monkeypatch.setattr(task_routes, "_task_store", lambda: DummyStore(task))
        return app

    return _factory


def _get_button_classes(html, button_id):
    block_pattern = rf'<[^>]*id="{button_id}"[^>]*>'
    match = re.search(block_pattern, html)
    assert match, f"Button with id={button_id} not found"
    class_match = re.search(r'class="([^"]+)"', match.group(0))
    assert class_match, f"Button with id={button_id} does not have a class attribute"
    return class_match.group(1)


def test_task2_active_shows_cancel_button(app_factory):
    task = {
        "id": "running-task",
        "title": "Demo",
        "status": "Running",
        "stages": {
            "Download": {"status": "Running", "number": 1}
        },
    }
    app = app_factory(task)
    with app.test_client() as client:
        response = client.get("/task2", query_string={"task_id": task["id"]})
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    cancel_classes = _get_button_classes(html, "cancel-task-btn")
    assert "d-none" not in cancel_classes
    assert f'data-task-id="{task["id"]}"' in html

    restart_classes = _get_button_classes(html, "restart-task-btn")
    assert "d-none" in restart_classes
    assert "badge text-bg-primary" in html  # running badge


def test_task2_terminal_shows_restart_button(app_factory):
    task = {
        "id": "complete-task",
        "title": "Demo",
        "status": "Completed",
        "stages": {
            "Download": {"status": "Completed", "number": 1}
        },
    }
    app = app_factory(task)
    with app.test_client() as client:
        response = client.get("/task2", query_string={"task_id": task["id"]})
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    cancel_classes = _get_button_classes(html, "cancel-task-btn")
    assert "d-none" in cancel_classes

    restart_classes = _get_button_classes(html, "restart-task-btn")
    assert "d-none" not in restart_classes
    assert f'data-task-id="{task["id"]}"' in html
    assert "badge text-bg-success" in html


def _test_stage_cancelled_renders_warning_badge(app_factory):
    task = {
        "id": "cancelled-task",
        "title": "Demo",
        "status": "Cancelled",
        "stages": {
            "Upload": {"status": "Cancelled", "number": 1}
        },
    }
    app = app_factory(task)
    with app.test_client() as client:
        response = client.get("/task2", query_string={"task_id": task["id"]})
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    header_badge = re.search(r'id="task_status"[^<]*<span class="badge ([^"]+)"', html)
    assert header_badge, "Expected status badge in header"
    assert "text-bg-warning" in header_badge.group(1)
    assert "Cancelled" in html

    assert 'badge text-bg-warning border border-warning">Cancelled' in html
