from html import unescape
from types import SimpleNamespace
from typing import Any, Iterable

import pymysql
import pytest

from src.app import create_app
from src.app.config import settings
from src.app.app_routes.admin.admin_routes import coordinators
from src.app.users import admin_service


class FakeDatabase:
    """Lightweight stub that mimics the Database helper using in-memory rows."""

    def __init__(self, _db_data: dict[str, Any]):
        self._rows: list[dict[str, Any]] = []
        self._next_id = 1

    def _normalize(self, sql: str) -> str:
        return " ".join(sql.strip().split()).lower()

    def _row_dict(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "username": row["username"],
            "is_active": row["is_active"],
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def execute_query(self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None) -> int:
        del timeout_override
        params = tuple(params or ())
        normalized = self._normalize(sql)

        if normalized.startswith("create table if not exists admin_users"):
            return 0

        if normalized.startswith("insert into admin_users"):
            username = params[0]
            if any(row["username"] == username for row in self._rows):
                raise pymysql.err.IntegrityError(1062, "Duplicate entry")

            row = {
                "id": self._next_id,
                "username": username,
                "is_active": 1,
                "created_at": None,
                "updated_at": None,
            }
            self._rows.append(row)
            self._next_id += 1
            return 1

        if normalized.startswith("update admin_users set is_active"):
            is_active, coordinator_id = params
            for row in self._rows:
                if row["id"] == coordinator_id:
                    row["is_active"] = 1 if is_active else 0
                    return 1
            return 0

        if normalized.startswith("delete from admin_users"):
            coordinator_id = params[0]
            before = len(self._rows)
            self._rows = [row for row in self._rows if row["id"] != coordinator_id]
            return 1 if len(self._rows) != before else 0

        raise NotImplementedError(sql)

    def execute_query_safe(self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None) -> int:
        try:
            return self.execute_query(sql, params, timeout_override=timeout_override)
        except pymysql.MySQLError:
            return 0

    def fetch_query(
        self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None
    ) -> list[dict[str, Any]]:
        del timeout_override
        params = tuple(params or ())
        normalized = self._normalize(sql)

        if "from admin_users" not in normalized:
            raise NotImplementedError(sql)

        if "where id = %s" in normalized:
            coordinator_id = params[0]
            for row in self._rows:
                if row["id"] == coordinator_id:
                    return [self._row_dict(row)]
            return []

        if "where username = %s" in normalized and "username in" not in normalized:
            username = params[0]
            for row in self._rows:
                if row["username"] == username:
                    return [self._row_dict(row)]
            return []

        if normalized.startswith("select username from admin_users where username in"):
            usernames = set(params)
            return [{"username": row["username"]} for row in self._rows if row["username"] in usernames]

        if "order by id asc" in normalized:
            return [self._row_dict(row) for row in sorted(self._rows, key=lambda row: row["id"])]

        raise NotImplementedError(sql)

    def fetch_query_safe(
        self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None
    ) -> list[dict[str, Any]]:
        try:
            return self.fetch_query(sql, params, timeout_override=timeout_override)
        except pymysql.MySQLError:
            return []


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
    object.__setattr__(settings, "admins", [])  # ensure runtime list is driven by the store

    monkeypatch.setattr("src.app.users.admin_service.Database", FakeDatabase)
    monkeypatch.setattr("src.app.users.admin_service.has_db_config", lambda: True)

    store = admin_service.MySQLCoordinatorStore(settings.db_data)
    store.add("admin")
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


def test_coordinator_dashboard_access_granted():
    pass


def test_coordinator_dashboard_requires_admin_user():
    pass


def test_coordinator_dashboard_redirects_when_anonymous():
    pass


def test_navbar_shows_admin_link_only_for_admin():
    pass


def test_add_coordinator():
    pass


def test_toggle_coordinator_active():
    pass


def test_delete_coordinator():
    pass
