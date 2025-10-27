import threading
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

from src.app import create_app
from src.app.app_routes.tasks import routes
from src.app.threads import task_threads, web_run_task
from src.app.db import TaskAlreadyExistsError


class InMemoryTaskStore:
    def __init__(self) -> None:
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_task(
        self,
        task_id: str,
        title: str,
        status: str = "Pending",
        username: str = "",
        form: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            if task_id in self.tasks:
                raise TaskAlreadyExistsError(self.tasks[task_id])
            self.tasks[task_id] = {
                "id": task_id,
                "title": title,
                "username": username,
                "status": status,
                "form": dict(form or {}),
            }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self.tasks.get(task_id)
            return dict(task) if task else None

    def get_active_task_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for task in self.tasks.values():
                if task["title"] == title and task["status"] not in {"Completed", "Failed", "Cancelled"}:
                    return dict(task)
        return None

    def update_status(self, task_id: str, status: str) -> None:
        with self._lock:
            if task_id in self.tasks:
                updated = dict(self.tasks[task_id])
                updated["status"] = status
                self.tasks[task_id] = updated

    def update_stage(self, task_id: str, stage_name: str, stage_state: Dict[str, Any]) -> None:  # pragma: no cover - unused
        pass

    def update_results(self, task_id: str, results: Dict[str, Any]) -> None:  # pragma: no cover - unused
        pass

    def update_data(self, task_id: str, data: Dict[str, Any]) -> None:  # pragma: no cover - unused
        pass

    def close(self) -> None:  # pragma: no cover - interface compatibility
        pass


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")

    user = SimpleNamespace(
        user_id=1,
        username="tester",
        access_token="token",
        access_secret="secret",
    )

    monkeypatch.setattr("src.app.users.current.current_user", lambda: user)

    from src.app.users import admin_service

    admin_service.set_store_for_testing(admin_service.InMemoryCoordinatorStore())

    app = create_app()
    app.config["TESTING"] = True

    store = InMemoryTaskStore()
    lock = threading.Lock()

    monkeypatch.setattr(routes, "_task_store", lambda: store)
    monkeypatch.setattr(routes, "current_user", lambda: user)
    routes.TASK_STORE = store
    routes.TASKS_LOCK = lock

    from src.app.app_routes.cancel_restart import routes as cancel_routes

    monkeypatch.setattr(cancel_routes, "_task_store", lambda: store)
    monkeypatch.setattr(cancel_routes, "current_user", lambda: user)
    cancel_routes.TASK_STORE = store
    cancel_routes.TASKS_LOCK = lock

    with task_threads.CANCEL_EVENTS_LOCK:
        task_threads.CANCEL_EVENTS.clear()

    return app


def test_cancel_route_signals_event_and_updates_status(app: Any, monkeypatch: pytest.MonkeyPatch):
    # TODO: FAILED tests/test_task_routes.py::test_cancel_route_signals_event_and_updates_status - assert False
    store: InMemoryTaskStore = routes._task_store()  # type: ignore[assignment]

    started = threading.Event()
    finished = threading.Event()

    def fake_run_task(db_data, task_id, title, args, user_payload, *, cancel_event=None):
        assert cancel_event is not None
        started.set()
        cancel_event.wait(1)
        finished.set()

    monkeypatch.setattr(task_threads, "run_task", fake_run_task)

    client = app.test_client()
    response = client.post("/", data={"title": "Sample"})
    assert response.status_code == 302
    assert started.wait(1)

    task_id = next(iter(store.tasks))
    with task_threads.CANCEL_EVENTS_LOCK:
        cancel_event = task_threads.CANCEL_EVENTS.get(task_id)
    assert cancel_event is not None and not cancel_event.is_set()

    cancel_response = client.post(f"/tasks/{task_id}/cancel")
    assert cancel_response.status_code == 200
    payload = cancel_response.get_json()
    assert payload == {"task_id": task_id, "status": "Cancelled"}

    assert store.tasks[task_id]["status"] == "Cancelled"

    assert finished.wait(1)
    with task_threads.CANCEL_EVENTS_LOCK:
        assert task_id not in task_threads.CANCEL_EVENTS


def test_restart_route_creates_new_task_and_replays_form(app: Any, monkeypatch: pytest.MonkeyPatch):
    # TODO: FAILED tests/test_task_routes.py::test_restart_route_creates_new_task_and_replays_form - KeyError: 'task_id'
    store: InMemoryTaskStore = routes._task_store()  # type: ignore[assignment]

    existing_id = "existing"
    store.create_task(existing_id, "Title", form={"title": "Title", "titles_limit": "5", "upload": "on"})
    store.update_status(existing_id, "Cancelled")

    captured: Dict[str, Any] = {}
    task_finished = threading.Event()

    def fake_run_task(db_data, task_id, title, args, user_payload, *, cancel_event=None):
        captured["task_id"] = task_id
        captured["title"] = title
        captured["args"] = args
        captured["user_payload"] = user_payload
        captured["cancel_event"] = cancel_event
        task_finished.set()

    monkeypatch.setattr(task_threads, "run_task", fake_run_task)

    client = app.test_client()
    restart_response = client.post(f"/tasks/{existing_id}/restart")
    assert restart_response.status_code == 200
    payload = restart_response.get_json()  # {'error': 'login-required'}
    new_task_id = payload["task_id"]

    assert task_finished.wait(timeout=1), "The fake_run_task did not run in time."

    assert new_task_id != existing_id
    assert new_task_id in store.tasks
    assert store.tasks[new_task_id]["title"] == "Title"
    assert store.tasks[new_task_id]["form"] == {"title": "Title", "titles_limit": "5", "upload": "on"}

    assert captured["task_id"] == new_task_id
    assert captured["title"] == "Title"
    assert hasattr(captured["args"], "titles_limit")
    assert captured["args"].titles_limit == 5
    assert captured["cancel_event"] is not None
    with task_threads.CANCEL_EVENTS_LOCK:
        assert new_task_id not in task_threads.CANCEL_EVENTS


def test_no_mysql_connection_attempted_with_default_settings(monkeypatch: pytest.MonkeyPatch):
    """
    Test that ensures no MySQL connection is attempted when create_app() is
    called with default test settings. This is achieved by patching the Database
    class and asserting that it is not instantiated.
    """
    database_init = threading.Event()

    def fake_database(*args, **kwargs):
        database_init.set()
        raise Exception("MySQL connection should not be attempted")

    monkeypatch.setattr("src.app.db.db_class.Database", fake_database)

    app = create_app()

    # Assert that the fake_database was not initialized, meaning no MySQL connection was attempted.
    assert not database_init.is_set()
