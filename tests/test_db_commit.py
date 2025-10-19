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


@pytest.fixture
def db_factory(monkeypatch):
    """
    Create a factory fixture that produces a Database instance backed by a mocked pymysql connection.
    
    The returned factory, when called with a module path, does the following:
    - Creates a mock cursor with context-manager support, an empty default fetch result, and a rowcount of 0.
    - Creates a mock connection whose cursor() returns the mock cursor and whose commit() is a mock.
    - Patches `pymysql.connect` to return that mock connection.
    - Imports the given module and instantiates its `Database` class with default connection parameters.
    - Returns a tuple `(db, connection, cursor)` where `db` is the Database instance, and `connection`/`cursor` are the mocks.
    
    Parameters:
        monkeypatch: pytest fixture used to apply the `pymysql.connect` patch.
    
    Returns:
        factory (callable): A function that accepts `module_name: str` and returns `(db, connection, cursor)`.
    """
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
    "src.web.db.db_class",
    "src.web.db.svg_db",
])
def test_execute_query_commits_for_writes(db_factory, module_name):
    db, connection, cursor = db_factory(module_name)
    cursor.rowcount = 3

    result = db.execute_query("INSERT INTO example VALUES (1)")

    connection.commit.assert_called_once()
    assert result == 3


@pytest.mark.parametrize("module_name", [
    "src.web.db.db_class",
    "src.web.db.svg_db",
])
def test_execute_query_skips_commit_for_select(db_factory, module_name):
    db, connection, cursor = db_factory(module_name)
    rows = [{"id": 1}]
    cursor.fetchall.return_value = rows

    result = db.execute_query("SELECT * FROM example")

    connection.commit.assert_not_called()
    assert result == rows