from __future__ import annotations

import json
# import threading
from typing import Any, Dict, Optional
import datetime

from svg_translate import logger
from .db import execute_query, fetch_query

TERMINAL_STATUSES = ("Completed", "Failed")


class TaskAlreadyExistsError(Exception):
    """Raised when attempting to create a duplicate active task."""

    def __init__(self, task: Dict[str, Any]):
        super().__init__("Task with this title is already in progress")
        self.task = task


def _serialize(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _normalize_title(title: str) -> str:
    """Return a normalized form of a title for duplicate detection."""
    return title.strip().casefold()


def _deserialize(value: Optional[str]) -> Any:
    if value is None:
        return None
    return json.loads(value)


class TaskStorePyMysql:
    """MySQL-backed task store using helper functions execute_query/fetch_query."""

    def __init__(self, _: str | None = None) -> None:
        # Note: db connection is managed inside execute_query/fetch_query
        # self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        """Create table and indexes if they don't exist."""
        # Use TEXT for JSON fields for wider MySQL compatibility.
        # If your MySQL supports JSON type, you can switch to JSON.
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id VARCHAR(128) PRIMARY KEY,
                title TEXT NOT NULL,
                normalized_title VARCHAR(512) NOT NULL,
                status VARCHAR(64) NOT NULL,
                form_json LONGTEXT NULL,
                data_json LONGTEXT NULL,
                results_json LONGTEXT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            "CREATE INDEX IF NOT EXISTS idx_tasks_norm ON tasks(normalized_title)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)"
        ]
        # MySQL before 8.0 does not accept "IF NOT EXISTS" on CREATE INDEX.
        # So we guard by checking INFORMATION_SCHEMA and creating conditionally.
        try:
            execute_query(ddl[0])
            # Conditionally create indexes for maximum compatibility
            existing = fetch_query(
                """
                SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tasks'
                """
            )
            existing_idx = {row["INDEX_NAME"] for row in existing}
            if "idx_tasks_norm" not in existing_idx:
                execute_query("CREATE INDEX idx_tasks_norm ON tasks(normalized_title)")
            if "idx_tasks_status" not in existing_idx:
                execute_query("CREATE INDEX idx_tasks_status ON tasks(status)")
            if "idx_tasks_created" not in existing_idx:
                execute_query("CREATE INDEX idx_tasks_created ON tasks(created_at)")
        except Exception as e:
            logger.warning("Failed to initialize schema: %s", e)

    def _current_ts(self) -> str:
        # Store in UTC. MySQL DATETIME has no TZ; keep application-level UTC.
        return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")

    def close(self) -> None:
        # No-op: connections are short-lived inside helpers.
        return

    def create_task(
        self,
        task_id: str,
        title: str,
        status: str = "Pending",
        form: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = self._current_ts()
        normalized_title = _normalize_title(title)
        # Application-level guard to ensure at most one active task per normalized_title.
        # with self._lock:
        try:
            # Check for an existing active task
            row = fetch_query(
                """
                SELECT * FROM tasks
                WHERE normalized_title = %s AND status NOT IN (%s, %s)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                [normalized_title, *TERMINAL_STATUSES],
            )
            if row:
                raise TaskAlreadyExistsError(self._row_to_task(row[0]))

            # Insert new task
            execute_query(
                """
                INSERT INTO tasks
                    (id, title, normalized_title, status, form_json, data_json, results_json, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    task_id,
                    title,
                    normalized_title,
                    status,
                    _serialize(form),
                    None,
                    None,
                    now,
                    now,
                ],
            )
        except TaskAlreadyExistsError:
            logger.error("TaskAlreadyExistsError")
            raise
        except Exception as e:
            logger.error(f"Failed to insert task, Error: {e}")
            raise

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            rows = fetch_query("SELECT * FROM tasks WHERE id = %s", [task_id])
        except Exception as e:
            logger.error(f"Failed to get task, Error: {e}")
            return None
        if not rows:
            return None
        return self._row_to_task(rows[0])

    def get_active_task_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        normalized_title = _normalize_title(title)
        try:
            rows = fetch_query(
                """
                SELECT * FROM tasks
                WHERE normalized_title = %s AND status NOT IN (%s, %s)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                [normalized_title, *TERMINAL_STATUSES],
            )
        except Exception as e:
            logger.error(f"Failed to get task, Error: {e}")
            return None
        if not rows:
            return None
        return self._row_to_task(rows[0])

    def update_task(
        self,
        task_id: str,
        *,
        title: Optional[str] = None,
        status: Optional[str] = None,
        form: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Prepare JSON and normalized title only when provided
        form_json = _serialize(form) if form is not None else None
        data_json = _serialize(data) if data is not None else None
        results_json = _serialize(results) if results is not None else None
        norm_title = _normalize_title(title) if title is not None else None

        # Early exit if nothing to update
        if all(v is None for v in (title, status, form, data, results)):
            return

        # Build dynamic UPDATE using COALESCE to keep existing values
        try:
            execute_query(
                """
                UPDATE tasks
                SET
                  title = COALESCE(%s, title),
                  normalized_title = COALESCE(%s, normalized_title),
                  status = COALESCE(%s, status),
                  form_json = COALESCE(%s, form_json),
                  data_json = COALESCE(%s, data_json),
                  results_json = COALESCE(%s, results_json),
                  updated_at = %s
                WHERE id = %s
                """,
                [
                    title,
                    norm_title,
                    status,
                    form_json,
                    data_json,
                    results_json,
                    self._current_ts(),
                    task_id,
                ],
            )
        except Exception as e:
            logger.error(f"Failed to update task, Error: {e}")

    def update_status(self, task_id: str, status: str) -> None:
        self.update_task(task_id, status=status)

    def update_data(self, task_id: str, data: Dict[str, Any]) -> None:
        self.update_task(task_id, data=data)

    def update_results(self, task_id: str, results: Dict[str, Any]) -> None:
        self.update_task(task_id, results=results)

    def _row_to_task(self, row: Dict[str, Any]) -> Dict[str, Any]:
        # row is a dict from pymysql DictCursor via fetch_query()
        return {
            "id": row["id"],
            "title": row["title"],
            "normalized_title": row["normalized_title"],
            "status": row["status"],
            "form": _deserialize(row.get("form_json")),
            "data": _deserialize(row.get("data_json")),
            "results": _deserialize(row.get("results_json")),
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        }
