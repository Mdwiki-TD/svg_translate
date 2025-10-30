"""Integration tests for the admin template management routes."""

from __future__ import annotations

from dataclasses import replace
from html import unescape
from types import SimpleNamespace
from typing import Any, Iterable

import pytest

from src.app import create_app, template_service
from src.app.template_service import TemplateRecord


class FakeTemplatesDB:
    """In-memory replacement for the MySQL-backed TemplatesDB helper."""

    def __init__(self, _db_data: dict[str, Any] | None = None):
        del _db_data
        self._records: list[TemplateRecord] = []
        self._next_id = 1

    # -- helpers -----------------------------------------------------------------
    def reset(self) -> None:
        self._records.clear()
        self._next_id = 1

    def _find_index(self, template_id: int) -> int:
        for index, record in enumerate(self._records):
            if record.id == template_id:
                return index
        raise LookupError(f"Template id {template_id} was not found")

    def list(self) -> list[TemplateRecord]:
        return list(self._records)

    def add(self, title: str, main_file: str) -> TemplateRecord:
        title = title.strip()
        main_file = main_file.strip()
        if not title:
            raise ValueError("Title is required")
        if any(record.title == title for record in self._records):
            raise ValueError(f"Template '{title}' already exists")

        record = TemplateRecord(id=self._next_id, title=title, main_file=main_file or None)
        self._records.append(record)
        self._next_id += 1
        return record

    def update(self, template_id: int, title: str, main_file: str) -> TemplateRecord:
        title = title.strip()
        main_file = main_file.strip()
        index = self._find_index(template_id)
        updated = replace(self._records[index], title=title, main_file=main_file or None)
        self._records[index] = updated
        return updated

    def delete(self, template_id: int) -> TemplateRecord:
        index = self._find_index(template_id)
        record = self._records.pop(index)
        return record

    def add_or_update(self, title: str, main_file: str) -> TemplateRecord:
        try:
            existing = next(record for record in self._records if record.title == title.strip())
        except StopIteration:
            return self.add(title, main_file)
        return self.update(existing.id, title, main_file)


def snapshot(records: Iterable[TemplateRecord]) -> list[tuple[int, str, str | None]]:
    return [(record.id, record.title, record.main_file) for record in records]


@pytest.fixture
def admin_templates_client(monkeypatch: pytest.MonkeyPatch):
    """Return a configured Flask test client paired with a fake templates store."""

    monkeypatch.setenv("FLASK_SECRET_KEY", "testing-secret")
    admin_user = SimpleNamespace(username="admin")

    def fake_current_user() -> SimpleNamespace:
        return admin_user

    monkeypatch.setattr("src.app.users.current.current_user", fake_current_user)
    monkeypatch.setattr(
        "src.app.app_routes.admin.admin_routes.templates.current_user", fake_current_user
    )
    monkeypatch.setattr("src.app.app_routes.admin.admin_required.current_user", fake_current_user)
    monkeypatch.setattr(
        "src.app.app_routes.admin.admin_required.active_coordinators", lambda: {admin_user.username}
    )
    monkeypatch.setattr(
        "src.app.users.admin_service.active_coordinators", lambda: {admin_user.username}
    )
    monkeypatch.setattr(
        "src.app.users.current.active_coordinators", lambda: {admin_user.username}
    )
    monkeypatch.setattr("src.app.users.admin_service.has_db_config", lambda: True)

    fake_store = FakeTemplatesDB({})
    fake_store.add("Existing Template", "existing.svg")

    monkeypatch.setattr("src.app.template_service.has_db_config", lambda: True)

    def fake_templates_factory(_db_data: dict[str, Any]):
        return fake_store

    monkeypatch.setattr("src.app.template_service.TemplatesDB", fake_templates_factory)

    template_service._TEMPLATE_STORE = fake_store

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    try:
        yield client, fake_store
    finally:
        template_service._TEMPLATE_STORE = None
        fake_store.reset()


def test_templates_dashboard_lists_existing_records(admin_templates_client):
    client, store = admin_templates_client

    store.add("Second Template", "second.svg")

    response = client.get("/admin/templates")
    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Templates" in page
    assert "Existing Template" in page
    assert "Second Template" in page
    assert "second.svg" in page


def test_add_template_persists_record_and_flashes_success(admin_templates_client):
    client, store = admin_templates_client

    before = len(store.list())
    response = client.post(
        "/admin/templates/add",
        data={"title": "New Template", "main_file": "new.svg"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Template 'New Template' added." in page

    records = store.list()
    assert len(records) == before + 1
    assert any(record.title == "New Template" and record.main_file == "new.svg" for record in records)


def test_update_template_mutates_store_and_flashes_success(admin_templates_client):
    client, store = admin_templates_client
    template_id = store.list()[0].id

    response = client.post(
        "/admin/templates/update",
        data={"id": str(template_id), "title": "Existing Template", "main_file": "updated.svg"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Template 'Existing Template' main file: updated.svg updated." in page

    record = next(record for record in store.list() if record.id == template_id)
    assert record.main_file == "updated.svg"


def test_delete_template_removes_record_and_flashes_success(admin_templates_client):
    client, store = admin_templates_client
    template_id = store.list()[0].id

    response = client.post(
        f"/admin/templates/{template_id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Template 'Existing Template' removed." in page
    assert not any(record.id == template_id for record in store.list())


def test_add_template_requires_title_and_preserves_store(admin_templates_client):
    client, store = admin_templates_client
    before = snapshot(store.list())

    response = client.post(
        "/admin/templates/add",
        data={"title": " ", "main_file": "ignored.svg"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Title is required to add a template." in page
    assert snapshot(store.list()) == before


def test_update_template_requires_identifier(admin_templates_client):
    client, store = admin_templates_client
    before = snapshot(store.list())

    response = client.post(
        "/admin/templates/update",
        data={"id": "", "title": "Existing Template", "main_file": "ignored.svg"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Template ID is required to update a template." in page
    assert snapshot(store.list()) == before


def test_update_template_requires_title(admin_templates_client):
    client, store = admin_templates_client
    template_id = store.list()[0].id
    before = snapshot(store.list())

    response = client.post(
        "/admin/templates/update",
        data={"id": str(template_id), "title": "   ", "main_file": "ignored.svg"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = unescape(response.get_data(as_text=True))
    assert "Title is required to update a template." in page
    assert snapshot(store.list()) == before
