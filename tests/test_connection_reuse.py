import os

import pytest


os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("OAUTH_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("OAUTH_CONSUMER_KEY", "test-consumer-key")
os.environ.setdefault("OAUTH_CONSUMER_SECRET", "test-consumer-secret")
os.environ.setdefault("OAUTH_MWURI", "https://example.org/w/index.php")


class FakeCursor:
    def __init__(self) -> None:
        self.description = None
        self.rowcount = 0

    def execute(self, sql: str, params=None) -> None:  # noqa: ANN001 - test helper signature
        statement = sql.strip().upper()
        if statement.startswith("SELECT"):
            self.description = ("column",)
            self.rowcount = 0
        else:
            self.description = None
            self.rowcount = 1

    def executemany(self, sql: str, params_seq):  # noqa: ANN001 - test helper signature
        self.description = None
        self.rowcount = len(list(params_seq))

    def fetchall(self):
        return []

    def close(self) -> None:
        pass


class FakeConnection:
    def cursor(self) -> FakeCursor:
        return FakeCursor()

    def ping(self, reconnect: bool = False) -> None:  # noqa: FBT002 - signature compatibility
        pass

    def close(self) -> None:
        pass

    def get_autocommit(self) -> bool:
        return True

    def rollback(self) -> None:
        pass

    def commit(self) -> None:
        pass


def test_sequential_requests_use_cached_connections(monkeypatch):
    connect_calls: list[tuple[tuple, dict]] = []

    def fake_connect(*args, **kwargs):
        connect_calls.append((args, kwargs))
        return FakeConnection()

    monkeypatch.setattr("src.app.db.db_class.pymysql.connect", fake_connect)
    monkeypatch.setattr("app.db.db_class.pymysql.connect", fake_connect)
    monkeypatch.setattr(
        "src.app.db.task_store_pymysql.TaskStorePyMysql._init_schema",
        lambda self: None,
    )
    monkeypatch.setattr(
        "app.db.task_store_pymysql.TaskStorePyMysql._init_schema",
        lambda self: None,
    )
    monkeypatch.setattr(
        "src.app.db.task_store_pymysql.TaskStorePyMysql.list_tasks",
        lambda self, **kwargs: [],
    )
    monkeypatch.setattr(
        "app.db.task_store_pymysql.TaskStorePyMysql.list_tasks",
        lambda self, **kwargs: [],
    )

    from app import create_app
    from app.users import store as user_store
    from app.tasks import routes as task_routes

    user_store._db = None
    task_routes.TASK_STORE = None

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    with client.session_transaction() as session:
        session["uid"] = 7

    response = client.get("/logout")
    assert response.status_code == 302

    response = client.get("/tasks")
    assert response.status_code == 200

    response = client.get("/tasks")
    assert response.status_code == 200

    assert len(connect_calls) <= 3
