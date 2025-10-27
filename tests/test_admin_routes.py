from html import unescape
from types import SimpleNamespace
from typing import Any

import pytest

from src.app import create_app
from src.app.config import settings
# from src.app.app_routes.admin import routes as admin_routes
from src.app.app_routes.admin.admin_routes import coordinators
from src.app.users import admin_service


def _set_current_user(monkeypatch: pytest.MonkeyPatch, user: Any) -> None:
    def _fake_current_user() -> Any:
        return user

    monkeypatch.setattr("src.app.users.current.current_user", _fake_current_user)
    monkeypatch.setattr("src.app.app_routes.admin.admin_routes.coordinators.current_user", _fake_current_user)
    monkeypatch.setattr("src.app.app_routes.admin.admin_required.current_user", _fake_current_user)
    monkeypatch.setattr("src.app.app_routes.main.routes.current_user", _fake_current_user)


@pytest.fixture
def app_and_store(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")
    original_admins = list(settings.admins)
    object.__setattr__(settings, "admins", ["admin"])  # ensure deterministic admin list

    store = admin_service.InMemoryCoordinatorStore(["admin"])
    admin_service.set_store_for_testing(store)

    coordinators.admin_service.set_store_for_testing(store)
    app = create_app()
    app.config["TESTING"] = True

    try:
        yield app, store
    finally:
        admin_service.set_store_for_testing(None)
        coordinators.admin_service.set_store_for_testing(None)
        object.__setattr__(settings, "admins", original_admins)


def test_coordinator_dashboard_access_granted(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, store = app_and_store
    _set_current_user(monkeypatch, SimpleNamespace(username="admin"))

    response = app.test_client().get("/admin/coordinators")
    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Coordinators" in page
    assert "Total Coordinators" in page
    assert "admin" in page


def test_coordinator_dashboard_requires_admin_user(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, _store = app_and_store
    _set_current_user(monkeypatch, SimpleNamespace(username="not_admin"))

    response = app.test_client().get("/admin/coordinators")
    assert response.status_code == 403


def test_coordinator_dashboard_redirects_when_anonymous(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, _store = app_and_store
    _set_current_user(monkeypatch, None)

    response = app.test_client().get("/admin/coordinators", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_navbar_shows_admin_link_only_for_admin(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, _store = app_and_store

    # Non-admin should not see the link
    _set_current_user(monkeypatch, SimpleNamespace(username="viewer"))
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)
    assert "Admins" not in html

    # Admin should see the link
    _set_current_user(monkeypatch, SimpleNamespace(username="admin"))
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)
    assert "Admins" in html


def test_add_coordinator(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, store = app_and_store
    _set_current_user(monkeypatch, SimpleNamespace(username="admin"))

    response = app.test_client().post("/admin/coordinators/add", data={"username": "new_admin"}, follow_redirects=True)
    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "new_admin" in page
    assert "Coordinator 'new_admin' added." in page
    assert "new_admin" in settings.admins
    assert any(record.username == "new_admin" for record in store.list())


def test_toggle_coordinator_active(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, store = app_and_store
    _set_current_user(monkeypatch, SimpleNamespace(username="admin"))

    new_record = store.add("helper")
    admin_service.set_coordinator_active(new_record.id, True)  # ensure sync

    response = app.test_client().post(
        f"/admin/coordinators/{new_record.id}/active",
        data={"active": "0"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Coordinator 'helper' deactivated." in unescape(response.get_data(as_text=True))
    assert "helper" not in settings.admins


def test_delete_coordinator(app_and_store, monkeypatch: pytest.MonkeyPatch):
    app, store = app_and_store
    _set_current_user(monkeypatch, SimpleNamespace(username="admin"))

    record = store.add("to_remove")
    admin_service.set_coordinator_active(record.id, True)

    response = app.test_client().post(
        f"/admin/coordinators/{record.id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Coordinator 'to_remove' removed." in unescape(response.get_data(as_text=True))
    assert "to_remove" not in settings.admins
    assert all(r.username != "to_remove" for r in store.list())
