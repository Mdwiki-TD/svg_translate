from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
import datetime
from pathlib import Path
from typing import Any, Dict, Optional


TERMINAL_STATUSES = ("Completed", "Failed")


class TaskAlreadyExistsError(Exception):
    """Raised when attempting to create a duplicate active task."""

    def __init__(self, task: Dict[str, Any]):
        super().__init__("Task with this title is already in progress")
        self.task = task


def _serialize(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value)


def _normalize_title(title: str) -> str:
    """Return a normalized form of a title for duplicate detection."""
    return title.strip().casefold()


def _deserialize(value: Optional[str]) -> Any:
    if value is None:
        return None
    return json.loads(value)


class TaskStore:
    """SQLite backed task store used by the web application."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.isolation_level = None
        self._lock = threading.Lock()
        # Improve concurrency characteristics
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")

        self._init_schema()

    def _init_schema(self) -> None:
        with self._write_transaction() as cursor:
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
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_active_lookup
                ON tasks (normalized_title, status)
                """
            )

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
        now = self._current_ts()

        # TODO:
        # The duplicate-title check in create_task is performed with a plain SELECT followed by an insert. Because there is no unique index or locking that spans processes, two concurrent web workers can both execute this block at the same time, each seeing no active task and then inserting their own row. The end result is multiple "Pending" tasks for the same normalized title, even though the route is supposed to enforce one active task at a time. Consider enforcing uniqueness at the database level (e.g. a unique partial index on normalized_title for non-terminal statuses or using BEGIN IMMEDIATE/INSERT … ON CONFLICT) so that duplicate submissions are rejected even under concurrent requests.

        with self._write_transaction() as cursor:
            normalized_title = _normalize_title(title)
            existing = cursor.execute(
                """
                SELECT * FROM tasks
                WHERE normalized_title = ? AND status NOT IN (?, ?)
                LIMIT 1
                """,
                (normalized_title, *TERMINAL_STATUSES)
            ).fetchone()
            if existing:
                raise TaskAlreadyExistsError(self._row_to_task(existing))
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

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_task(row)

    def get_active_task_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        normalized_title = _normalize_title(title)
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM tasks
                WHERE normalized_title = ? AND status NOT IN (?, ?)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (normalized_title, *TERMINAL_STATUSES)
            ).fetchone()
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
        fields: Dict[str, Any] = {}

        if title is not None:
            fields["title"] = title
            fields["normalized_title"] = _normalize_title(title)

        if status is not None:
            fields["status"] = status

        if form is not None:
            fields["form_json"] = _serialize(form)

        if data is not None:
            fields["data_json"] = _serialize(data)

        if results is not None:
            fields["results_json"] = _serialize(results)

        if not fields:
            return

        set_clause = ", ".join(f"{column} = ?" for column in fields)
        params = list(fields.values())
        params.append(self._current_ts())
        params.append(task_id)

        with self._write_transaction() as cursor:
            cursor.execute(
                f"""
                UPDATE tasks
                SET {set_clause}, updated_at = ?
                WHERE id = ?
                """,
                params,
            )

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
