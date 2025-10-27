from __future__ import annotations

import logging
from typing import Any, Dict, Optional

# from .utils import DbUtils
# from .db_TasksListDB import TasksListDB
# from .db_StageStore import StageStore

logger = logging.getLogger(__name__)
TERMINAL_STATUSES = ("Completed", "Failed", "Cancelled")
TERMINAL_PLACEHOLDERS = ", ".join(["%s"] * len(TERMINAL_STATUSES))


class TaskAlreadyExistsError(Exception):
    """Raised when attempting to create a duplicate active task."""

    def __init__(self, task: Dict[str, Any]):
        """
        Initialize the exception with the conflicting task.

        Parameters:
            task (Dict[str, Any]): The existing active task that caused the conflict; stored on the exception as the `task` attribute.
        """
        super().__init__("Task with this title is already in progress")
        self.task = task


class CreateUpdateTask:  # (StageStore, TasksListDB, DbUtils):
    """MySQL-backed task store using helper functions execute_query/fetch_query."""

    def __init__(self) -> None:
        pass

    def create_task(
        self,
        task_id: str,
        title: str,
        status: str = "Pending",
        username: str = "",
        form: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a new task row in the database while enforcing that at most one non-terminal task exists for the same normalized title.

        Parameters:
            task_id (str): Unique identifier for the task.
            title (str): Human-readable title; a normalized form (trimmed, casefolded) is used to detect duplicates.
            status (str): Initial task status (default "Pending").
            form (Optional[Dict[str, Any]]): Optional form payload to store as JSON.

        Raises:
            TaskAlreadyExistsError: If an existing non-terminal task with the same normalized title is found.
            Exception: Propagates any underlying database or execution errors encountered during insert.
        """
        now = self._current_ts()
        normalized_name = self._normalize_title(title)
        # Application-level guard to ensure at most one active task per normalized_name.
        # with self._lock:
        if not form or not form.get("ignore_existing_task"):
            # Check for an existing active task
            rows = self.db.fetch_query(
                f"""
                    SELECT
                        t.*,
                        ts.stage_name AS stage_name,
                        ts.stage_number AS stage_number,
                        ts.stage_status AS stage_status,
                        ts.stage_sub_name AS stage_sub_name,
                        ts.stage_message AS stage_message,
                        ts.updated_at AS stage_updated_at
                    FROM (
                        SELECT * FROM tasks
                        WHERE normalized_title = %s AND status NOT IN ({TERMINAL_PLACEHOLDERS})
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) AS t
                    LEFT JOIN task_stages ts ON t.id = ts.task_id
                    ORDER BY COALESCE(ts.stage_number, 0) ASC
                    """,
                [normalized_name, *TERMINAL_STATUSES],
            )
            if rows:
                task_rows, stage_map = self._rows_to_tasks_with_stages(rows)
                existing_task_row = task_rows[0]
                existing_task = self._row_to_task(
                    existing_task_row,
                    stages=stage_map.get(existing_task_row["id"], {})  # or self.fetch_stages(existing_task_row["id"])
                )
                raise TaskAlreadyExistsError(existing_task)
        try:
            # Insert new task
            self.db.execute_query(
                """
                INSERT INTO tasks
                    (id, username, title, normalized_title, status, form_json, data_json, results_json, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    task_id,
                    username,
                    title,
                    normalized_name,
                    status,
                    self._serialize(form),
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
        """
        Retrieve a task by its identifier.

        Parameters:
            task_id (str): The task's unique identifier.

        Returns:
            A dictionary representing the task with deserialized JSON fields and ISO-formatted timestamps, or `None` if the task does not exist or an error occurred while fetching it.
        """
        rows = self.db.fetch_query_safe(
            """
            SELECT
                t.*,
                ts.stage_name AS stage_name,
                ts.stage_number AS stage_number,
                ts.stage_status AS stage_status,
                ts.stage_sub_name AS stage_sub_name,
                ts.stage_message AS stage_message,
                ts.updated_at AS stage_updated_at
            FROM tasks AS t
            LEFT JOIN task_stages ts ON t.id = ts.task_id
            WHERE t.id = %s
            ORDER BY COALESCE(ts.stage_number, 0) ASC
            """,
            [task_id],
        )
        if not rows:
            logger.error("Failed to get task")
            return None

        task_rows, stage_map = self._rows_to_tasks_with_stages(rows)
        if not task_rows:
            logger.error("Failed to get task")
            return None

        task_row = task_rows[0]
        return self._row_to_task(
            task_row,
            stages=stage_map.get(task_row["id"], {})  # or self.fetch_stages(task_row["id"])
        )

    def get_active_task_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent active task whose title matches the given title after trimming and casefold normalization.

        Parameters:
            title (str): Title to match; whitespace is stripped and casefolded before lookup.

        Returns:
            dict: Task dictionary with deserialized JSON fields and ISO-formatted timestamps, or `None` if no active task is found or an error occurs.
        """
        normalized_name = self._normalize_title(title)
        rows = self.db.fetch_query_safe(
            f"""
            SELECT
                t.*,
                ts.stage_name AS stage_name,
                ts.stage_number AS stage_number,
                ts.stage_status AS stage_status,
                ts.stage_sub_name AS stage_sub_name,
                ts.stage_message AS stage_message,
                ts.updated_at AS stage_updated_at
            FROM (
                SELECT * FROM tasks
                WHERE normalized_title = %s AND status NOT IN ({TERMINAL_PLACEHOLDERS})
                ORDER BY created_at DESC
                LIMIT 1
            ) AS t
            LEFT JOIN task_stages ts ON t.id = ts.task_id
            ORDER BY COALESCE(ts.stage_number, 0) ASC
            """,
            [normalized_name, *TERMINAL_STATUSES],
        )
        if not rows:
            logger.error("Failed to get task")
            return None

        task_rows, stage_map = self._rows_to_tasks_with_stages(rows)
        if not task_rows:
            logger.error("Failed to get task")
            return None

        task_row = task_rows[0]
        return self._row_to_task(
            task_row,
            stages=stage_map.get(task_row["id"], {})  # or self.fetch_stages(task_row["id"])
        )

    def update_task(
        self,
        task_id: str,
        *,
        title: Optional[str] = None,
        status: Optional[str] = None,
        form: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None,
        main_file: str | None = None
    ) -> None:
        # Prepare JSON and normalized title only when provided
        """
        Update fields of an existing task, applying only the provided values and leaving other columns unchanged.

        Only parameters passed as non-None are applied. JSON-like payloads (form, data, results) are serialized before storage. The task's updated_at timestamp is set to the current UTC time.

        Parameters:
            task_id (str): Identifier of the task to update.
            title (Optional[str]): New title for the task; when provided, a normalized_title is also stored.
            status (Optional[str]): New status for the task.
            form (Optional[Dict[str, Any]]): New form payload to store (will be JSON-serialized).
            data (Optional[Dict[str, Any]]): New data payload to store (will be JSON-serialized).
            results (Optional[Dict[str, Any]]): New results payload to store (will be JSON-serialized).
        """
        form_json = self._serialize(form) if form is not None else None
        if data is not None and isinstance(data, dict) and "stages" in data:
            data = dict(data)
            data.pop("stages", None)
        data_json = self._serialize(data) if data is not None else None

        results_json = self._serialize(results) if results is not None else None
        norm_title = self._normalize_title(title) if title is not None else None
        main_file = main_file if main_file else None

        # Early exit if nothing to update
        if all(v is None for v in (title, status, form, data, results)):
            return

        # Build dynamic UPDATE using COALESCE to keep existing values
        try:
            self.db.execute_query(
                """
                UPDATE tasks
                SET
                  title = COALESCE(%s, title),
                  normalized_title = COALESCE(%s, normalized_title),
                  main_file = COALESCE(%s, main_file),
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
                    main_file,
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
        """
        Set the status of the task identified by task_id.

        Parameters:
            task_id (str): The unique identifier of the task to update.
            status (str): The new status value to assign to the task.
        """
        self.update_task(task_id, status=status)

    def update_data(self, task_id: str, data: Dict[str, Any]) -> None:
        """
        Set the task's data payload to the provided dictionary.

        Parameters:
            task_id (str): ID of the task to update.
            data (Dict[str, Any]): JSON-serializable payload to store in the task's data field.
        """
        self.update_task(task_id, data=data)

    def update_results(self, task_id: str, results: Dict[str, Any]) -> None:
        """
        Set the results payload for an existing task.

        Updates the task identified by `task_id` to store the provided `results` payload.

        Parameters:
            task_id (str): Identifier of the task to update.
            results (Dict[str, Any]): Results payload to store for the task.
        """
        self.update_task(task_id, results=results)

    def update_main_title(self, task_id: str, main_title: str) -> None:
        """
        Set the status of the task identified by task_id.

        Parameters:
            task_id (str): The unique identifier of the task to update.
            main_title (str): The new value.
        """
        self.update_task(task_id, main_file=main_title)

    def update_task_one_column(
        self,
        task_id: str,
        column_name: str,
        column_value: Any,
    ) -> None:
        sql = f"UPDATE tasks SET {column_name} = %s WHERE id = %s"

        try:
            self.db.execute_query(
                sql,
                [column_value, task_id],
            )
        except Exception:
            logger.error(f"Failed to update '{column_name}' for task {task_id}")
