import threading
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

import pytest
from pytest import FixtureRequest

from src.app import create_app
from src.app.config import settings
from src.app.app_routes.tasks import routes as task_routes
from src.app.app_routes.admin import routes as admin_routes


class InMemoryTaskStore:
    def __init__(self) -> None:
        self._tasks: List[Dict[str, Any]] = []

    def add_task(self, task: Dict[str, Any]) -> None:
        self._tasks.append(dict(task))

    def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        username: Optional[str] = None,
        order_by: str | None = None,
        descending: bool = False,
    ) -> List[Dict[str, Any]]:
        tasks: Iterable[Dict[str, Any]] = list(self._tasks)
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        if username:
            tasks = [task for task in tasks if task.get("username") == username]
        tasks = list(tasks)
        if descending:
            tasks.reverse()
        return [dict(task) for task in tasks]

    def close(self) -> None:  # pragma: no cover - compatibility shim
        pass


def _set_current_user(monkeypatch: pytest.MonkeyPatch, user: Any) -> None:
    def _fake_current_user() -> Any:
        return user

    monkeypatch.setattr("src.app.users.current.current_user", _fake_current_user)
    monkeypatch.setattr("src.app.app_routes.admin.routes.current_user", _fake_current_user)
    monkeypatch.setattr("src.app.app_routes.main.routes.current_user", _fake_current_user)


@pytest.fixture
def app_and_store(monkeypatch: pytest.MonkeyPatch, request: FixtureRequest):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")
    original_admins = list(settings.admins)
    object.__setattr__(settings, "admins", ["admin"])  # ensure deterministic admin list
    request.addfinalizer(lambda: object.__setattr__(settings, "admins", original_admins))

    app = create_app()
    app.config["TESTING"] = True

    store = InMemoryTaskStore()
    monkeypatch.setattr(task_routes, "_task_store", lambda: store)
    monkeypatch.setattr(admin_routes, "_task_store", lambda: store)
    task_routes.TASK_STORE = store
    admin_routes.TASKS_LOCK = task_routes.TASKS_LOCK = threading.Lock()

    return app, store


def test_admin_dashboard_access_granted(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, store = app_and_store

    store.add_task(
        {
            "id": "task-1",
            "title": "Translate icons",
            "status": "Running",
            "username": "editor",
            "created_at": "2024-01-01 12:00:00",
            "updated_at": "2024-01-01 12:30:00",
            "results": {"new_translations_count": 2, "files_to_upload_count": 1},
        }
    )
    store.add_task(
        {
            "id": "task-2",
            "title": "Upload batch",
            "status": "Completed",
            "username": "other",
            "created_at": "2024-01-02 10:00:00",
            "updated_at": "2024-01-02 11:00:00",
            "results": {"new_translations_count": 5, "files_to_upload_count": 5},
        }
    )

    _set_current_user(monkeypatch, SimpleNamespace(username="admin"))

    response = app.test_client().get("/admin")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Admin Dashboard" in page
    assert "Translate icons" in page
    assert "Total Tasks" in page
    assert "Active Tasks" in page


def test_admin_dashboard_requires_admin_user(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, _store = app_and_store
    _set_current_user(monkeypatch, SimpleNamespace(username="not_admin"))

    response = app.test_client().get("/admin")
    assert response.status_code == 403


def test_admin_dashboard_redirects_when_anonymous(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, _store = app_and_store
    _set_current_user(monkeypatch, None)

    response = app.test_client().get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_navbar_shows_admin_link_only_for_admin(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, _store = app_and_store

    # Non-admin should not see the link
    _set_current_user(monkeypatch, SimpleNamespace(username="viewer"))
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)
    assert "Admin Dashboard" not in html

    # Admin should see the link
    _set_current_user(monkeypatch, SimpleNamespace(username="admin"))
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)
    assert "Admin Dashboard" in html
