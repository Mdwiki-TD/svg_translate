from __future__ import annotations

import json
# import threading
from typing import Any, Dict, Iterable, List, Optional
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
            """
            CREATE TABLE IF NOT EXISTS task_stages (
                stage_id VARCHAR(255) PRIMARY KEY,
                task_id VARCHAR(128) NOT NULL,
                stage_name VARCHAR(255) NOT NULL,
                stage_number INT NOT NULL,
                stage_status VARCHAR(64) NOT NULL,
                stage_sub_name LONGTEXT NULL,
                stage_message LONGTEXT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT fk_task_stage_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                CONSTRAINT uq_task_stage UNIQUE (task_id, stage_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
        ]
        # MySQL before 8.0 does not accept "IF NOT EXISTS" on CREATE INDEX.
        # So we guard by checking INFORMATION_SCHEMA and creating conditionally.
        try:
            execute_query(ddl[0])
            execute_query(ddl[1])
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
            existing_stage_idx = fetch_query(
                """
                SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'task_stages'
                """
            )
            existing_stage_idx_names = {row["INDEX_NAME"] for row in existing_stage_idx}
            if "idx_task_stages_task" not in existing_stage_idx_names:
                execute_query("CREATE INDEX idx_task_stages_task ON task_stages(task_id, stage_number)")
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
        if data is not None and isinstance(data, dict) and "stages" in data:
            data = dict(data)
            data.pop("stages", None)
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

    def replace_stages(self, task_id: str, stages: Dict[str, Dict[str, Any]]) -> None:
        now = self._current_ts()
        try:
            execute_query("DELETE FROM task_stages WHERE task_id = %s", [task_id])
            for stage_name, stage_data in stages.items():
                execute_query(
                    """
                    INSERT INTO task_stages (
                        stage_id,
                        task_id,
                        stage_name,
                        stage_number,
                        stage_status,
                        stage_sub_name,
                        stage_message,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        stage_number = VALUES(stage_number),
                        stage_status = VALUES(stage_status),
                        stage_sub_name = VALUES(stage_sub_name),
                        stage_message = VALUES(stage_message),
                        updated_at = VALUES(updated_at)
                    """,
                    [
                        f"{task_id}:{stage_name}",
                        task_id,
                        stage_name,
                        stage_data.get("number", 0),
                        stage_data.get("status", "Pending"),
                        stage_data.get("sub_name"),
                        stage_data.get("message"),
                        now,
                    ],
                )
        except Exception as exc:
            logger.error("Failed to replace task stages: %s", exc)

    def update_stage(self, task_id: str, stage_name: str, stage_data: Dict[str, Any]) -> None:
        now = self._current_ts()
        try:
            execute_query(
                """
                INSERT INTO task_stages (
                    stage_id,
                    task_id,
                    stage_name,
                    stage_number,
                    stage_status,
                    stage_sub_name,
                    stage_message,
                    updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    stage_number = COALESCE(VALUES(stage_number), stage_number),
                    stage_status = COALESCE(VALUES(stage_status), stage_status),
                    stage_sub_name = COALESCE(VALUES(stage_sub_name), stage_sub_name),
                    stage_message = COALESCE(VALUES(stage_message), stage_message),
                    updated_at = VALUES(updated_at)
                """,
                [
                    f"{task_id}:{stage_name}",
                    task_id,
                    stage_name,
                    stage_data.get("number"),
                    stage_data.get("status"),
                    stage_data.get("sub_name"),
                    stage_data.get("message"),
                    now,
                ],
            )
        except Exception as exc:
            logger.error("Failed to update stage '%s' for task %s: %s", stage_name, task_id, exc)

    def _fetch_stages(self, task_id: str) -> Dict[str, Dict[str, Any]]:
        try:
            rows = fetch_query(
                """
                SELECT stage_name, stage_number, stage_status, stage_sub_name, stage_message, updated_at
                FROM task_stages
                WHERE task_id = %s
                ORDER BY stage_number
                """,
                [task_id],
            )
        except Exception as exc:
            logger.error("Failed to fetch stages for task %s: %s", task_id, exc)
            return {}

        stages: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            updated_at = row["updated_at"]
            if hasattr(updated_at, "isoformat"):
                updated_str = updated_at.isoformat()
            else:
                updated_str = str(updated_at) if updated_at is not None else None
            stages[row["stage_name"]] = {
                "number": row["stage_number"],
                "status": row["stage_status"],
                "sub_name": row.get("stage_sub_name"),
                "message": row.get("stage_message"),
                "updated_at": updated_str,
            }
        return stages

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
            "stages": self._fetch_stages(row["id"]),
        }

    def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        statuses: Optional[Iterable[str]] = None,
        order_by: str = "created_at",
        descending: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        allowed_order_columns = {"created_at", "updated_at", "title", "status"}
        order_column = order_by if order_by in allowed_order_columns else "created_at"

        query_parts = ["SELECT * FROM tasks"]
        where_clauses = []
        params: List[Any] = []

        filter_statuses: List[str] = []
        if statuses:
            filter_statuses.extend([s for s in statuses if s is not None])
        if status:
            filter_statuses.append(status)

        if filter_statuses:
            placeholders = ", ".join(["%s"] * len(filter_statuses))
            where_clauses.append(f"status IN ({placeholders})")
            params.extend(filter_statuses)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        direction = "DESC" if descending else "ASC"
        query_parts.append(f"ORDER BY {order_column} {direction}")

        if limit is not None:
            query_parts.append("LIMIT %s")
            params.append(limit)
        if offset is not None:
            if limit is None:
                query_parts.append("LIMIT 18446744073709551615")
            query_parts.append("OFFSET %s")
            params.append(offset)

        sql = " ".join(query_parts)
        try:
            rows = fetch_query(sql, params)
        except Exception as exc:
            logger.error("Failed to list tasks, Error: %s", exc)
            return []

        return [self._row_to_task(row) for row in rows]
