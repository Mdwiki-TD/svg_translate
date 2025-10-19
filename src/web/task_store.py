from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from svg_translate import logger

TERMINAL_STATUSES = ("Completed", "Failed")


class TaskAlreadyExistsError(Exception):
    """Raised when attempting to create a duplicate active task."""

    def __init__(self, task: Dict[str, Any]):
        super().__init__("Task with this title is already in progress")
        self.task = task


def _serialize(value: Any) -> Optional[str]:
    """
    Serialize a Python value to a JSON string or return None for a missing value.
    
    Parameters:
        value (Any): The value to serialize; if None, no serialization is performed.
    
    Returns:
        Optional[str]: JSON string representation of `value`, or `None` if `value` is None.
    """
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _normalize_title(title: str) -> str:
    """
    Produce a canonical form of a title for duplicate detection.
    
    Returns:
        A string with surrounding whitespace removed and casefolded for case-insensitive comparison.
    """
    return title.strip().casefold()


def _deserialize(value: Optional[str]) -> Any:
    if value is None:
        return None
    return json.loads(value)


class TaskStore:
    """SQLite backed task store used by the web application."""

    def __init__(self, db_path: Path | str) -> None:
        """
        Initialize a TaskStore backed by the SQLite database at the given path.
        
        Opens and configures a SQLite connection for use across threads, stores the filesystem path, creates a threading lock for write serialization, and ensures the database schema is initialized.
        
        Parameters:
            db_path (Path | str): Filesystem path to the SQLite database file.
        """
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.isolation_level = None
        self._lock = threading.Lock()

        self._init_schema()

    def _init_schema(self) -> None:
        """
        Ensure the tasks table and required indexes exist in the SQLite database.
        
        Creates the tasks table (id, title, normalized_title, status, form_json, data_json, results_json, created_at, updated_at),
        adds indexes for normalized_title, status, and created_at, and creates a unique partial index that enforces at most one
        non-terminal (status not in 'Completed' or 'Failed') task per normalized_title. If schema creation fails with an
        sqlite3.OperationalError, a warning is logged.
        """
        with self._write_transaction() as cursor:
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        normalized_title TEXT NOT NULL,
                        status TEXT NOT NULL,
                        form_json TEXT,
                        data_json TEXT,
                        results_json TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                # Lookup/sort indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_norm ON tasks(normalized_title)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
                # Enforce at most one active task per normalized_title
                cursor.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_title "
                    "ON tasks(normalized_title) "
                    "WHERE status NOT IN ('Completed','Failed')"
                )
            except sqlite3.OperationalError as e:
                logger.warning("Failed to initialize schema: %s", e)

    @contextmanager
    def _write_transaction(self):
        with self._lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute("BEGIN")
                yield cursor
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            finally:
                cursor.close()

    def _current_ts(self) -> str:
        return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")

    def close(self) -> None:
        self._conn.close()

    def create_task(
        self,
        task_id: str,
        title: str,
        *,
        status: str = "Pending",
        form: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a new task record in the store.
        
        Inserts a task row with the given id, title, status, and optional JSON payloads (form, data, results). The title is normalized for duplicate detection and JSON fields are serialized before storage. If another non-terminal task exists with the same normalized title, raises TaskAlreadyExistsError containing the existing task.
        
        Parameters:
            task_id (str): Unique identifier for the task to create.
            title (str): Human-readable task title; used to derive the normalized title for uniqueness checks.
            status (str, optional): Initial task status. Defaults to "Pending".
            form (dict | None, optional): Optional form payload to store; will be serialized to JSON.
            data (dict | None, optional): Optional data payload to store; will be serialized to JSON.
            results (dict | None, optional): Optional results payload to store; will be serialized to JSON.
        
        Raises:
            TaskAlreadyExistsError: If an active (non-terminal) task with the same normalized title already exists. The exception carries the existing task's data.
        """
        now = self._current_ts()

        with self._write_transaction() as cursor:
            normalized_title = _normalize_title(title)
            # ---
            try:
                cursor.execute(
                    """
                    INSERT INTO tasks (id, title, normalized_title, status, form_json, data_json, results_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        title,
                        normalized_title,
                        status,
                        _serialize(form),
                        _serialize(data),
                        _serialize(results),
                        now,
                        now,
                    ),

                )
            except sqlite3.IntegrityError as e:
                # Unique active-title constraint hit: fetch existing and raise
                row = cursor.execute(
                    "SELECT * FROM tasks WHERE normalized_title = ? AND status NOT IN (?, ?) ORDER BY created_at DESC LIMIT 1",
                    (normalized_title, *TERMINAL_STATUSES)
                ).fetchone()
                if row:
                    raise TaskAlreadyExistsError(self._row_to_task(row) if row else {"id": None, "title": title})
                else:
                    logger.error(f"Failed to insert new task, Error: {e}")
                    raise

            except Exception as e:
                logger.error(f"Failed to insert task, Error: {e}")
                raise

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = None
        with self._lock:
            try:
                row = self._conn.execute(
                    "SELECT * FROM tasks WHERE id = ?",
                    (task_id,)
                ).fetchone()
            except Exception as e:
                logger.error(f"Failed to get task, Error: {e}")
                return None

        if not row:
            return None
        return self._row_to_task(row)

    def get_active_task_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        normalized_title = _normalize_title(title)
        with self._lock:
            try:
                row = self._conn.execute(
                    """
                    SELECT * FROM tasks
                    WHERE normalized_title = ? AND status NOT IN (?, ?)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (normalized_title, *TERMINAL_STATUSES)
                ).fetchone()
            except Exception as e:
                logger.error(f"Failed to get task, Error: {e}")
                return None
        if not row:
            return None
        return self._row_to_task(row)

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

        # Prepare JSON fields
        form_json = _serialize(form) if form is not None else None
        data_json = _serialize(data) if data is not None else None
        results_json = _serialize(results) if results is not None else None
        # Compute normalized title only when title is provided
        norm_title = _normalize_title(title) if title is not None else None

        # Early exit if nothing to update
        if all(v is None for v in (title, status, form, data, results)):
            return

        with self._write_transaction() as cursor:
            try:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET
                    title = COALESCE(?, title),
                    normalized_title = COALESCE(?, normalized_title),
                    status = COALESCE(?, status),
                    form_json = COALESCE(?, form_json),
                    data_json = COALESCE(?, data_json),
                    results_json = COALESCE(?, results_json),
                    updated_at = ?
                    WHERE id = ?
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

    def _row_to_task(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "normalized_title": row["normalized_title"],
            "status": row["status"],
            "form": _deserialize(row["form_json"]),
            "data": _deserialize(row["data_json"]),
            "results": _deserialize(row["results_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }