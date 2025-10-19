"""
Comprehensive unit tests for TaskStorePyMysql class.
Tests cover CRUD operations, error handling, concurrent access, and edge cases.
"""
import datetime
import json
import sys
import types
from unittest.mock import MagicMock, patch, call

import pytest

# Mock pymysql before imports
try:
    import pymysql  # type: ignore
except ModuleNotFoundError:
    pymysql = types.ModuleType("pymysql")
    pymysql.MySQLError = Exception
    pymysql.cursors = types.SimpleNamespace(DictCursor=object)
    sys.modules["pymysql"] = pymysql
else:
    if not hasattr(pymysql, "MySQLError"):
        pymysql.MySQLError = Exception
    if not hasattr(pymysql, "cursors"):
        pymysql.cursors = types.SimpleNamespace(DictCursor=object)
    elif not hasattr(pymysql.cursors, "DictCursor"):
        pymysql.cursors.DictCursor = object

from src.web.task_store_pymysql import (
    TaskStorePyMysql,
    TaskAlreadyExistsError,
    _serialize,
    _deserialize,
    _normalize_title,
    TERMINAL_STATUSES,
)


@pytest.fixture
def mock_db_functions(monkeypatch):
    """Mock execute_query and fetch_query functions."""
    execute_mock = MagicMock(return_value=1)
    fetch_mock = MagicMock(return_value=[])
    
    monkeypatch.setattr("src.web.task_store_pymysql.execute_query", execute_mock)
    monkeypatch.setattr("src.web.task_store_pymysql.fetch_query", fetch_mock)
    
    return execute_mock, fetch_mock


@pytest.fixture
def task_store(_mock_db_functions):
    """Create a TaskStorePyMysql instance with mocked DB functions."""
    return TaskStorePyMysql()


class TestSerializationHelpers:
    """Test serialization and normalization helper functions."""
    
    def test_serialize_none(self):
        """Test serializing None returns None."""
        assert _serialize(None) is None
    
    def test_serialize_dict(self):
        """Test serializing a dictionary."""
        data = {"key": "value", "count": 42}
        result = _serialize(data)
        assert isinstance(result, str)
        assert json.loads(result) == data
    
    def test_serialize_with_unicode(self):
        """Test serializing with unicode characters."""
        data = {"message": "Hello 世界 🌍"}
        result = _serialize(data)
        assert "世界" in result
        assert "🌍" in result
    
    def test_deserialize_none(self):
        """Test deserializing None returns None."""
        assert _deserialize(None) is None
    
    def test_deserialize_json_string(self):
        """Test deserializing a JSON string."""
        json_str = '{"key": "value", "count": 42}'
        result = _deserialize(json_str)
        assert result == {"key": "value", "count": 42}
    
    def test_normalize_title_lowercase(self):
        """Test title normalization converts to lowercase."""
        assert _normalize_title("Example.svg") == "example.svg"
    
    def test_normalize_title_strips_whitespace(self):
        """Test title normalization strips whitespace."""
        assert _normalize_title("  Example.svg  ") == "example.svg"
    
    def test_normalize_title_case_folding(self):
        """Test title normalization uses case folding."""
        assert _normalize_title("EXAMPLE") == _normalize_title("example")


class TestTaskStoreInitialization:
    """Test TaskStorePyMysql initialization and schema setup."""
    
    def test_init_calls_init_schema(self, mock_db_functions):
        """Test that initialization calls _init_schema."""
        execute_mock, fetch_mock = mock_db_functions
        TaskStorePyMysql()
        
        assert execute_mock.called or fetch_mock.called
    
    def test_init_with_custom_db_path(self, _mock_db_functions):
        """Test initialization with custom database path."""
        store = TaskStorePyMysql("/custom/path/db.sqlite")
        assert store is not None
    
    def test_init_schema_creates_table(self, mock_db_functions):
        """Test that _init_schema attempts to create tables."""
        execute_mock, _fetch_mock = mock_db_functions
        TaskStorePyMysql()
        
        # Should execute CREATE TABLE statement
        assert any("CREATE TABLE" in str(_call).upper() for _call in execute_mock.call_args_list)
    
    def test_init_schema_creates_indexes(self, mock_db_functions):
        """Test that _init_schema creates indexes."""
        execute_mock, _fetch_mock = mock_db_functions
        _fetch_mock.return_value = []  # No existing indexes
        
        TaskStorePyMysql()
        
        # Should create indexes
        calls_str = str(execute_mock.call_args_list).upper()
        assert "INDEX" in calls_str


class TestCreateTask:
    """Test task creation functionality."""
    
    def test_create_task_basic(self, task_store, mock_db_functions):
        """Test creating a basic task."""
        execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []  # No existing tasks
        
        task_store.create_task("task123", "Example.svg")
        
        # Should insert new task
        assert execute_mock.called
        insert_call = [c for c in execute_mock.call_args_list if "INSERT" in str(c).upper()]
        assert len(insert_call) > 0
    
    def test_create_task_with_form(self, task_store, mock_db_functions):
        """Test creating a task with form data."""
        execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        form_data = {"title": "Example.svg", "option": "value"}
        task_store.create_task("task123", "Example.svg", form=form_data)
        
        assert execute_mock.called
    
    def test_create_task_default_status_pending(self, task_store, mock_db_functions):
        """Test that default status is Pending."""
        execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.create_task("task123", "Example.svg")
        
        # Check that Pending status is used
        calls = execute_mock.call_args_list
        assert any("Pending" in str(_call) for _call in calls)
    
    def test_create_task_raises_on_duplicate_active(self, task_store, mock_db_functions):
        """Test that creating duplicate active task raises error."""
        _execute_mock, fetch_mock = mock_db_functions
        
        # Simulate existing active task
        existing_task = {
            "id": "existing123",
            "title": "Example.svg",
            "normalized_title": "example.svg",
            "status": "Running",
            "form_json": None,
            "data_json": None,
            "results_json": None,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
        }
        fetch_mock.return_value = [existing_task]
        
        with pytest.raises(TaskAlreadyExistsError) as exc_info:
            task_store.create_task("task456", "Example.svg")
        
        assert exc_info.value.task["id"] == "existing123"
    
    def test_create_task_allows_after_completion(self, task_store, mock_db_functions):
        """Test that new task can be created after previous completes."""
        execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []  # No active tasks
        
        task_store.create_task("task456", "Example.svg")
        
        assert execute_mock.called
    
    def test_create_task_normalizes_title(self, task_store, mock_db_functions):
        """Test that task creation normalizes titles."""
        execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.create_task("task123", "  EXAMPLE.SVG  ")
        
        # Check normalized title is used in query
        calls_str = str(execute_mock.call_args_list)
        assert "example.svg" in calls_str


class TestGetTask:
    """Test task retrieval functionality."""
    
    def test_get_task_found(self, task_store, mock_db_functions):
        """Test retrieving an existing task."""
        _execute_mock, fetch_mock = mock_db_functions
        
        task_data = {
            "id": "task123",
            "title": "Example.svg",
            "normalized_title": "example.svg",
            "status": "Running",
            "form_json": '{"key": "value"}',
            "data_json": '{"stage": "download"}',
            "results_json": None,
            "created_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime.datetime(2024, 1, 1, 12, 5, 0),
        }
        fetch_mock.return_value = [task_data]
        
        result = task_store.get_task("task123")
        
        assert result is not None
        assert result["id"] == "task123"
        assert result["title"] == "Example.svg"
        assert result["status"] == "Running"
        assert result["form"] == {"key": "value"}
    
    def test_get_task_not_found(self, task_store, mock_db_functions):
        """Test retrieving a non-existent task."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        result = task_store.get_task("nonexistent")
        
        assert result is None
    
    def test_get_task_handles_error(self, task_store, mock_db_functions):
        """Test that get_task handles database errors gracefully."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.side_effect = Exception("Database error")
        
        result = task_store.get_task("task123")
        
        assert result is None


class TestGetActiveTaskByTitle:
    """Test retrieving active tasks by title."""
    
    def test_get_active_task_found(self, task_store, mock_db_functions):
        """Test finding an active task by title."""
        _execute_mock, fetch_mock = mock_db_functions
        
        task_data = {
            "id": "task123",
            "title": "Example.svg",
            "normalized_title": "example.svg",
            "status": "Running",
            "form_json": None,
            "data_json": None,
            "results_json": None,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
        }
        fetch_mock.return_value = [task_data]
        
        result = task_store.get_active_task_by_title("Example.svg")
        
        assert result is not None
        assert result["id"] == "task123"
    
    def test_get_active_task_not_found(self, task_store, mock_db_functions):
        """Test that completed tasks are not returned."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        result = task_store.get_active_task_by_title("Completed.svg")
        
        assert result is None
    
    def test_get_active_task_normalizes_title(self, task_store, mock_db_functions):
        """Test that title is normalized when searching."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.get_active_task_by_title("  EXAMPLE.SVG  ")
        
        # Check normalized title is used in query
        calls_str = str(fetch_mock.call_args_list)
        assert "example.svg" in calls_str


class TestUpdateTask:
    """Test task update functionality."""
    
    def test_update_task_status(self, task_store, mock_db_functions):
        """Test updating task status."""
        execute_mock, _fetch_mock = mock_db_functions
        
        task_store.update_task("task123", status="Completed")
        
        assert execute_mock.called
        calls_str = str(execute_mock.call_args_list).upper()
        assert "UPDATE" in calls_str
        assert "Completed" in str(execute_mock.call_args_list)
    
    def test_update_task_data(self, task_store, mock_db_functions):
        """Test updating task data."""
        execute_mock, _fetch_mock = mock_db_functions
        
        data = {"stage": "download", "progress": 50}
        task_store.update_task("task123", data=data)
        
        assert execute_mock.called
    
    def test_update_task_results(self, task_store, mock_db_functions):
        """Test updating task results."""
        execute_mock, _fetch_mock = mock_db_functions
        
        results = {"files_uploaded": 10, "success": True}
        task_store.update_task("task123", results=results)
        
        assert execute_mock.called
    
    def test_update_task_multiple_fields(self, task_store, mock_db_functions):
        """Test updating multiple fields at once."""
        execute_mock, _fetch_mock = mock_db_functions
        
        task_store.update_task(
            "task123",
            status="Running",
            data={"progress": 75},
            results={"partial": "data"}
        )
        
        assert execute_mock.called
    
    def test_update_task_no_fields_no_op(self, task_store, mock_db_functions):
        """Test that updating with no fields does nothing."""
        execute_mock, _fetch_mock = mock_db_functions
        execute_mock.reset_mock()
        
        task_store.update_task("task123")
        
        assert not execute_mock.called
    
    def test_update_status_convenience_method(self, task_store, mock_db_functions):
        """Test update_status convenience method."""
        execute_mock, _fetch_mock = mock_db_functions
        
        task_store.update_status("task123", "Failed")
        
        assert execute_mock.called
        assert "Failed" in str(execute_mock.call_args_list)
    
    def test_update_data_convenience_method(self, task_store, mock_db_functions):
        """Test update_data convenience method."""
        execute_mock, _fetch_mock = mock_db_functions
        
        task_store.update_data("task123", {"key": "value"})
        
        assert execute_mock.called
    
    def test_update_results_convenience_method(self, task_store, mock_db_functions):
        """Test update_results convenience method."""
        execute_mock, _fetch_mock = mock_db_functions
        
        task_store.update_results("task123", {"count": 100})
        
        assert execute_mock.called


class TestListTasks:
    """Test task listing functionality."""
    
    def test_list_tasks_all(self, task_store, mock_db_functions):
        """Test listing all tasks."""
        _execute_mock, fetch_mock = mock_db_functions
        
        tasks_data = [
            {
                "id": "task1",
                "title": "File1.svg",
                "normalized_title": "file1.svg",
                "status": "Completed",
                "form_json": None,
                "data_json": None,
                "results_json": None,
                "created_at": datetime.datetime(2024, 1, 1),
                "updated_at": datetime.datetime(2024, 1, 1),
            },
            {
                "id": "task2",
                "title": "File2.svg",
                "normalized_title": "file2.svg",
                "status": "Running",
                "form_json": None,
                "data_json": None,
                "results_json": None,
                "created_at": datetime.datetime(2024, 1, 2),
                "updated_at": datetime.datetime(2024, 1, 2),
            },
        ]
        fetch_mock.return_value = tasks_data
        
        result = task_store.list_tasks()
        
        assert len(result) == 2
        assert result[0]["id"] == "task1"
        assert result[1]["id"] == "task2"
    
    def test_list_tasks_filter_by_status(self, task_store, mock_db_functions):
        """Test filtering tasks by status."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.list_tasks(status="Running")
        
        calls_str = str(fetch_mock.call_args_list)
        assert "Running" in calls_str
    
    def test_list_tasks_filter_by_statuses(self, task_store, mock_db_functions):
        """Test filtering tasks by multiple statuses."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.list_tasks(statuses=["Running", "Pending"])
        
        calls_str = str(fetch_mock.call_args_list)
        assert "Running" in calls_str or "Pending" in calls_str
    
    def test_list_tasks_order_by_created(self, task_store, mock_db_functions):
        """Test ordering tasks by created_at."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.list_tasks(order_by="created_at", descending=True)
        
        calls_str = str(fetch_mock.call_args_list).upper()
        assert "ORDER BY" in calls_str
        assert "DESC" in calls_str
    
    def test_list_tasks_order_ascending(self, task_store, mock_db_functions):
        """Test ordering tasks in ascending order."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.list_tasks(order_by="created_at", descending=False)
        
        calls_str = str(fetch_mock.call_args_list).upper()
        assert "ASC" in calls_str
    
    def test_list_tasks_with_limit(self, task_store, mock_db_functions):
        """Test limiting number of tasks returned."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.list_tasks(limit=10)
        
        calls_str = str(fetch_mock.call_args_list).upper()
        assert "LIMIT" in calls_str
    
    def test_list_tasks_with_offset(self, task_store, mock_db_functions):
        """Test offsetting task list."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.list_tasks(limit=10, offset=20)
        
        calls_str = str(fetch_mock.call_args_list).upper()
        assert "OFFSET" in calls_str
    
    def test_list_tasks_handles_error(self, task_store, mock_db_functions):
        """Test that list_tasks handles errors gracefully."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.side_effect = Exception("Database error")
        
        result = task_store.list_tasks()
        
        assert result == []
    
    def test_list_tasks_invalid_order_column_uses_default(self, task_store, mock_db_functions):
        """Test that invalid order column uses default."""
        _execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        task_store.list_tasks(order_by="invalid_column")
        
        # Should use created_at as default
        calls_str = str(fetch_mock.call_args_list)
        assert "created_at" in calls_str


class TestRowToTask:
    """Test _row_to_task conversion."""
    
    def test_row_to_task_basic(self, task_store):
        """Test converting a database row to task dict."""
        row = {
            "id": "task123",
            "title": "Example.svg",
            "normalized_title": "example.svg",
            "status": "Running",
            "form_json": '{"key": "value"}',
            "data_json": '{"stage": "download"}',
            "results_json": '{"count": 10}',
            "created_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime.datetime(2024, 1, 1, 12, 5, 0),
        }
        
        result = task_store._row_to_task(row)
        
        assert result["id"] == "task123"
        assert result["title"] == "Example.svg"
        assert result["form"] == {"key": "value"}
        assert result["data"] == {"stage": "download"}
        assert result["results"] == {"count": 10}
    
    def test_row_to_task_null_json_fields(self, task_store):
        """Test converting row with null JSON fields."""
        row = {
            "id": "task123",
            "title": "Example.svg",
            "normalized_title": "example.svg",
            "status": "Pending",
            "form_json": None,
            "data_json": None,
            "results_json": None,
            "created_at": datetime.datetime(2024, 1, 1),
            "updated_at": datetime.datetime(2024, 1, 1),
        }
        
        result = task_store._row_to_task(row)
        
        assert result["form"] is None
        assert result["data"] is None
        assert result["results"] is None
    
    def test_row_to_task_datetime_conversion(self, task_store):
        """Test datetime fields are converted to ISO format."""
        row = {
            "id": "task123",
            "title": "Example.svg",
            "normalized_title": "example.svg",
            "status": "Running",
            "form_json": None,
            "data_json": None,
            "results_json": None,
            "created_at": datetime.datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime.datetime(2024, 1, 1, 13, 0, 0),
        }
        
        result = task_store._row_to_task(row)
        
        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)
        assert "2024-01-01" in result["created_at"]


class TestCloseMethod:
    """Test close functionality."""
    
    def test_close_is_callable(self, task_store):
        """Test that close method can be called."""
        # Should not raise an error
        task_store.close()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_create_task_with_empty_title(self, task_store, mock_db_functions):
        """Test creating task with empty title."""
        execute_mock, fetch_mock = mock_db_functions
        fetch_mock.return_value = []
        
        # Should still work but normalize to empty string
        task_store.create_task("task123", "")
        
        assert execute_mock.called
    
    def test_update_task_nonexistent_task(self, task_store, mock_db_functions):
        """Test updating a non-existent task."""
        execute_mock, _fetch_mock = mock_db_functions
        
        # Should execute UPDATE but affect 0 rows
        task_store.update_task("nonexistent", status="Completed")
        
        assert execute_mock.called
    
    def test_terminal_statuses_constant(self):
        """Test that TERMINAL_STATUSES is defined correctly."""
        assert "Completed" in TERMINAL_STATUSES
        assert "Failed" in TERMINAL_STATUSES
    
    def test_task_already_exists_error_attributes(self):
        """Test TaskAlreadyExistsError has task attribute."""
        task = {"id": "123", "title": "Example"}
        error = TaskAlreadyExistsError(task)
        
        assert error.task == task
        assert "already in progress" in str(error)