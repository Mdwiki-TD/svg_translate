import importlib
import sys
import time
import types
from unittest.mock import MagicMock

import pytest

try:
    import pymysql  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - executed when pymysql is unavailable
    pymysql = types.ModuleType("pymysql")
    pymysql.MySQLError = Exception
    pymysql.err = types.SimpleNamespace(OperationalError=Exception, InterfaceError=Exception)
    pymysql.cursors = types.SimpleNamespace(DictCursor=object)
    sys.modules["pymysql"] = pymysql
else:  # pragma: no cover - executed when pymysql is available
    if not hasattr(pymysql, "MySQLError"):
        pymysql.MySQLError = Exception
    if not hasattr(pymysql, "err"):
        pymysql.err = types.SimpleNamespace(OperationalError=pymysql.MySQLError, InterfaceError=pymysql.MySQLError)
    if not hasattr(pymysql, "cursors"):
        pymysql.cursors = types.SimpleNamespace(DictCursor=object)
    elif not hasattr(pymysql.cursors, "DictCursor"):
        pymysql.cursors.DictCursor = object


TEST_DB_PASSWORD = "password"  # noqa: S105


@pytest.fixture
def db_factory(monkeypatch):
    def _factory(module_name: str):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchall.return_value = []
        cursor.rowcount = 0
        cursor.description = None

        connection = MagicMock()
        connection.cursor.return_value = cursor
        connection.commit = MagicMock()
        connection.get_autocommit = MagicMock(return_value=True)

        monkeypatch.setattr(pymysql, "connect", MagicMock(return_value=connection))

        module = importlib.import_module(module_name)

        db = module.Database({
            "host": "localhost",
            "user": "user",
            "dbname": "database",
            "password": "password",
        })

        return db, connection, cursor

    return _factory


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_commits_for_writes(db_factory, module_name):
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 3
    connection.get_autocommit.return_value = False

    result = db.execute_query("INSERT INTO example VALUES (1)")

    connection.commit.assert_called_once()
    assert result == 3


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_skips_commit_for_select(db_factory, module_name):
    db, connection, cursor = db_factory(module_name)
    rows = [{"id": 1}]
    cursor.fetchall.return_value = rows
    cursor.description = ("id",)

    result = db.execute_query("SELECT * FROM example")

    connection.commit.assert_not_called()
    assert result == rows


# Additional comprehensive tests for Database classes

@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_database_initialization(db_factory, module_name):
    """Test that Database initializes with correct configuration."""
    db, _connection, _cursor = db_factory(module_name)

    assert db.host == "localhost"
    assert db.user == "user"
    assert db.dbname == "database"
    assert db.password == TEST_DB_PASSWORD


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_with_params(db_factory, module_name):
    """Test execute_query with parameterized queries."""
    db, _connection, cursor = db_factory(module_name)
    cursor.rowcount = 1

    result = db.execute_query("INSERT INTO users VALUES (%s, %s)", ("john", "doe"))

    cursor.execute.assert_called_once()
    assert result == 1


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_update_commits(db_factory, module_name):
    """Test that UPDATE queries commit changes."""
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 2
    connection.get_autocommit.return_value = False

    result = db.execute_query("UPDATE users SET name='Jane' WHERE id=1")

    connection.commit.assert_called_once()
    assert result == 2


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_delete_commits(db_factory, module_name):
    """Test that DELETE queries commit changes."""
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 5
    connection.get_autocommit.return_value = False

    result = db.execute_query("DELETE FROM users WHERE active=0")

    connection.commit.assert_called_once()
    assert result == 5


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_handles_errors(db_factory, module_name):
    """Test that execute_query propagates MySQL errors."""
    db, _connection, cursor = db_factory(module_name)
    cursor.execute.side_effect = pymysql.MySQLError("Connection lost")

    with pytest.raises(pymysql.MySQLError):
        db.execute_query("SELECT * FROM users")


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_fetch_all_returns_results(db_factory, module_name):
    """Test fetch_all returns fetched results."""
    db, connection, cursor = db_factory(module_name)
    expected = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    cursor.fetchall.return_value = expected
    cursor.description = ("id",)

    result = db.fetch_all("SELECT * FROM users")

    assert result == expected
    connection.commit.assert_not_called()


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_fetch_all_with_params(db_factory, module_name):
    """Test fetch_all with parameterized queries."""
    db, _connection, cursor = db_factory(module_name)
    expected = [{"id": 1, "name": "Alice"}]
    cursor.fetchall.return_value = expected
    cursor.description = ("id",)

    result = db.fetch_all("SELECT * FROM users WHERE id = %s", [1])

    cursor.execute.assert_called_once()
    assert result == expected


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_fetch_all_handles_errors(db_factory, module_name):
    """Test that fetch_all propagates MySQL errors."""
    db, _connection, cursor = db_factory(module_name)
    cursor.execute.side_effect = pymysql.MySQLError("Table not found")

    with pytest.raises(pymysql.MySQLError):
        db.fetch_all("SELECT * FROM nonexistent")


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_select_case_insensitive(db_factory, module_name):
    """Test that SELECT detection is case-insensitive."""
    db, connection, cursor = db_factory(module_name)
    expected = [{"count": 42}]
    cursor.fetchall.return_value = expected
    cursor.description = ("count",)

    result = db.execute_query("  select count(*) from users")

    connection.commit.assert_not_called()
    assert result == expected


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
])
def test_execute_query_whitespace_handling(db_factory, module_name):
    """Test execute_query handles queries with leading whitespace."""
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 1
    connection.get_autocommit.return_value = False

    result = db.execute_query("\n\t  INSERT INTO logs VALUES (1)")

    connection.commit.assert_called_once()
    assert result == 1




def test_fetch_all_safe_returns_empty_on_error(db_factory):
    db, _connection, cursor = db_factory("src.web.db.db_class")
    cursor.execute.side_effect = pymysql.MySQLError("boom")

    result = db.fetch_all_safe("SELECT * FROM demo")

    assert result == []


def test_execute_query_safe_returns_zero_on_error(db_factory):
    db, _connection, cursor = db_factory("src.web.db.db_class")
    cursor.execute.side_effect = pymysql.MySQLError("boom")

    result = db.execute_query_safe("UPDATE demo SET value=%s", [1])

    assert result == 0


def test_ensure_connection_recovers_after_ping_failure(monkeypatch):
    first_connection = MagicMock()
    second_connection = MagicMock()
    first_connection.ping.side_effect = pymysql.err.OperationalError(2006, "gone away")

    connect_mock = MagicMock(side_effect=[first_connection, second_connection])
    monkeypatch.setattr(pymysql, "connect", connect_mock)

    from src.web.db.db_class import Database

    db = Database({
        "host": "localhost",
        "user": "user",
        "dbname": "database",
        "password": "password",
    })

    db._ensure_connection()

    first_connection.close.assert_called_once()
    assert db.connection is second_connection


def test_execute_query_retries_on_transient_error(monkeypatch):
    cursor_first = MagicMock()
    cursor_second = MagicMock()
    cursor_first.execute.side_effect = pymysql.err.OperationalError(2006, "gone away")
    cursor_second.rowcount = 1
    cursor_first.description = None
    cursor_second.description = None

    first_conn = MagicMock()
    second_conn = MagicMock()
    first_conn.cursor.return_value = cursor_first
    second_conn.cursor.return_value = cursor_second

    connect_mock = MagicMock(side_effect=[first_conn, second_conn])
    monkeypatch.setattr(pymysql, "connect", connect_mock)

    from src.web.db.db_class import Database

    db = Database({
        "host": "localhost",
        "user": "user",
        "dbname": "database",
        "password": "password",
    })

    monkeypatch.setattr(db, "BASE_BACKOFF", 0)
    monkeypatch.setattr(time, "sleep", MagicMock())

    result = db.execute_query("UPDATE demo SET value=%s", [1])

    assert result == 1
    assert cursor_first.execute.call_count == 1
    assert cursor_second.execute.call_count == 1
    assert connect_mock.call_count == 2


def test_database_connection_error_exits(monkeypatch):
    """Test that Database initialization exits on connection error."""
    monkeypatch.setattr(pymysql, "connect", MagicMock(side_effect=pymysql.MySQLError("Connection refused")))

    from src.web.db import db_class

    with pytest.raises(SystemExit):
        db_class.Database({
            "host": "badhost",
            "user": "user",
            "dbname": "db",
            "password": "pass",
        })
