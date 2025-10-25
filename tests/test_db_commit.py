import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

try:
    import pymysql  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - executed when pymysql is unavailable
    pymysql = types.ModuleType("pymysql")
    pymysql.MySQLError = Exception
    pymysql.cursors = types.SimpleNamespace(DictCursor=object)
    sys.modules["pymysql"] = pymysql
else:  # pragma: no cover - executed when pymysql is available
    if not hasattr(pymysql, "MySQLError"):
        pymysql.MySQLError = Exception
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

        connection = MagicMock()
        connection.cursor.return_value = cursor
        connection.commit = MagicMock()

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
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_execute_query_commits_for_writes(db_factory, module_name):
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 3

    result = db.execute_query("INSERT INTO example VALUES (1)")

    connection.commit.assert_called_once()
    assert result == 3


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_execute_query_skips_commit_for_select(db_factory, module_name):
    db, connection, cursor = db_factory(module_name)
    rows = [{"id": 1}]
    cursor.fetchall.return_value = rows

    result = db.execute_query("SELECT * FROM example")

    connection.commit.assert_not_called()
    assert result == rows


# Additional comprehensive tests for Database classes

@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_database_initialization(db_factory, module_name):
    """Test that Database initializes with correct configuration."""
    db, _connection, _cursor = db_factory(module_name)

    assert db.host == "localhost"
    assert db.user == "user"
    assert db.dbname == "database"
    assert db.password == TEST_DB_PASSWORD


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_execute_query_with_params(db_factory, module_name):
    """Test execute_query with parameterized queries."""
    db, _connection, cursor = db_factory(module_name)
    cursor.rowcount = 1

    result = db.execute_query("INSERT INTO users VALUES (%s, %s)", ("john", "doe"))

    cursor.execute.assert_called_once()
    assert result == 1


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_execute_query_update_commits(db_factory, module_name):
    """Test that UPDATE queries commit changes."""
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 2

    result = db.execute_query("UPDATE users SET name='Jane' WHERE id=1")

    connection.commit.assert_called_once()
    assert result == 2


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_execute_query_delete_commits(db_factory, module_name):
    """Test that DELETE queries commit changes."""
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 5

    result = db.execute_query("DELETE FROM users WHERE active=0")

    connection.commit.assert_called_once()
    assert result == 5


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
])
def test_execute_query_handles_errors(db_factory, module_name):
    """Test that execute_query handles MySQL errors gracefully."""
    db, _connection, cursor = db_factory(module_name)
    cursor.execute.side_effect = pymysql.MySQLError("Connection lost")

    result = db.execute_query("SELECT * FROM users")

    # Should return empty list on error
    assert result == []


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_fetch_query_returns_results(db_factory, module_name):
    """Test fetch_query returns fetched results."""
    db, connection, cursor = db_factory(module_name)
    expected = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    cursor.fetchall.return_value = expected

    result = db.fetch_query("SELECT * FROM users")

    assert result == expected
    connection.commit.assert_not_called()


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_fetch_query_with_params(db_factory, module_name):
    """Test fetch_query with parameterized queries."""
    db, _connection, cursor = db_factory(module_name)
    expected = [{"id": 1, "name": "Alice"}]
    cursor.fetchall.return_value = expected

    result = db.fetch_query("SELECT * FROM users WHERE id = %s", [1])

    cursor.execute.assert_called_once()
    assert result == expected


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
])
def test_fetch_query_handles_errors(db_factory, module_name):
    """Test that fetch_query handles MySQL errors gracefully."""
    db, _connection, cursor = db_factory(module_name)
    cursor.execute.side_effect = pymysql.MySQLError("Table not found")

    result = db.fetch_query("SELECT * FROM nonexistent")

    assert result == []


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_execute_query_select_case_insensitive(db_factory, module_name):
    """Test that SELECT detection is case-insensitive."""
    db, connection, cursor = db_factory(module_name)
    expected = [{"count": 42}]
    cursor.fetchall.return_value = expected

    result = db.execute_query("  select count(*) from users")

    connection.commit.assert_not_called()
    assert result == expected


@pytest.mark.parametrize("module_name", [
    "src.app.db.db_class",
    "src.app.db.svg_db",
])
def test_execute_query_whitespace_handling(db_factory, module_name):
    """Test execute_query handles queries with leading whitespace."""
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 1

    result = db.execute_query("\n\t  INSERT INTO logs VALUES (1)")

    connection.commit.assert_called_once()
    assert result == 1


def test_svg_db_execute_query_helper(monkeypatch):
    """Test svg_db module-level execute_query helper function."""
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    cursor.rowcount = 3

    connection = MagicMock()
    connection.cursor.return_value = cursor
    connection.commit = MagicMock()

    monkeypatch.setattr(pymysql, "connect", MagicMock(return_value=connection))

    from src.app.db import svg_db
    monkeypatch.setattr(svg_db, "db_data", {
        "host": "localhost",
        "user": "user",
        "dbname": "test",
        "password": "pass",
    })

    result = svg_db.execute_query("INSERT INTO test VALUES (1)")

    assert result == 3


def test_svg_db_execute_query_helper_with_params(monkeypatch):
    """Test svg_db execute_query with parameters."""
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    cursor.rowcount = 1

    connection = MagicMock()
    connection.cursor.return_value = cursor

    monkeypatch.setattr(pymysql, "connect", MagicMock(return_value=connection))

    from src.app.db import svg_db
    monkeypatch.setattr(svg_db, "db_data", {
        "host": "localhost",
        "user": "user",
        "dbname": "test",
        "password": "pass",
    })

    result = svg_db.execute_query("INSERT INTO test VALUES (%s)", ["value"])

    assert result == 1


def test_svg_db_fetch_query_helper(monkeypatch):
    """Test svg_db module-level fetch_query helper function."""
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    expected = [{"id": 1}]
    cursor.fetchall.return_value = expected

    connection = MagicMock()
    connection.cursor.return_value = cursor

    monkeypatch.setattr(pymysql, "connect", MagicMock(return_value=connection))

    from src.app.db import svg_db
    monkeypatch.setattr(svg_db, "db_data", {
        "host": "localhost",
        "user": "user",
        "dbname": "test",
        "password": "pass",
    })

    result = svg_db.fetch_query("SELECT * FROM test")

    assert result == expected


def test_svg_db_fetch_query_helper_with_params(monkeypatch):
    """Test svg_db fetch_query with parameters."""
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    expected = [{"id": 1, "name": "test"}]
    cursor.fetchall.return_value = expected

    connection = MagicMock()
    connection.cursor.return_value = cursor

    monkeypatch.setattr(pymysql, "connect", MagicMock(return_value=connection))

    from src.app.db import svg_db
    monkeypatch.setattr(svg_db, "db_data", {
        "host": "localhost",
        "user": "user",
        "dbname": "test",
        "password": "pass",
    })

    result = svg_db.fetch_query("SELECT * FROM test WHERE id = %s", [1])

    assert result == expected


def test_database_connection_error_exits(monkeypatch):
    """Test that Database initialization exits on connection error."""
    monkeypatch.setattr(pymysql, "connect", MagicMock(side_effect=pymysql.MySQLError("Connection refused")))

    from src.app.db import db_class

    with pytest.raises(SystemExit):
        db_class.Database({
            "host": "badhost",
            "user": "user",
            "dbname": "db",
            "password": "pass",
        })
