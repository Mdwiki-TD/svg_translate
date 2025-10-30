"""Unit tests for db_CreateUpdate module."""
from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest

from src.app.db.db_CreateUpdate import CreateUpdateTask, TaskAlreadyExistsError


def test_delete_task_success(caplog):
    """Test successful task deletion with info logging."""
    mock_db = Mock()
    mock_db.execute_query = Mock(return_value=1)
    
    task_store = CreateUpdateTask(db=mock_db)
    
    with caplog.at_level(logging.INFO):
        task_store.delete_task("task123")
    
    mock_db.execute_query.assert_called_once()
    assert "Task task123 deleted successfully" in caplog.text


def test_delete_task_raises_and_logs_exception(caplog):
    """Test that delete_task logs exception and re-raises."""
    mock_db = Mock()
    mock_db.execute_query = Mock(side_effect=Exception("Database error"))
    
    task_store = CreateUpdateTask(db=mock_db)
    
    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception, match="Database error"):
            task_store.delete_task("task456")
    
    # Verify that logger.exception was called (logs at ERROR level with traceback)
    assert "Failed to delete task" in caplog.text
    assert "Database error" in caplog.text


def test_delete_task_sql_injection_prevention():
    """Test that delete_task uses parameterized queries."""
    mock_db = Mock()
    
    task_store = CreateUpdateTask(db=mock_db)
    task_store.delete_task("task' OR '1'='1")
    
    # Verify parameterized query
    call_args = mock_db.execute_query.call_args
    assert call_args[0][0].strip().startswith("DELETE FROM tasks")
    assert call_args[0][1] == ["task' OR '1'='1"]


def test_task_already_exists_error_stores_task():
    """Test TaskAlreadyExistsError stores the conflicting task."""
    conflicting_task = {"id": "task123", "title": "Test"}
    
    error = TaskAlreadyExistsError(conflicting_task)
    
    assert error.task == conflicting_task
    assert "Task with this title is already in progress" in str(error)


def test_logger_uses_svg_translate_name():
    """Test that the logger uses 'svg_translate' instead of __name__."""
    from src.app.db import db_CreateUpdate
    assert db_CreateUpdate.logger.name == "svg_translate"