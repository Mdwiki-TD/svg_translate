from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from svg_translate import logger

from .db_class import Database
from .utils import _serialize, _normalize_title, _deserialize, _current_ts

TERMINAL_STATUSES = ("Completed", "Failed")


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


class StageStore:
    """Utility mixin providing CRUD helpers for task stage persistence."""

    def update_stage(self, task_id: str, stage_name: str, stage_data: Dict[str, Any]) -> None:
        """Insert or update a single stage row for the given task.

        Parameters:
            task_id (str): Identifier of the owning task.
            stage_name (str): Logical stage key (e.g., "download").
            stage_data (dict): Metadata describing the stage, including number,
                status, sub_name, and message fields.

        Side Effects:
            Persists the stage to ``task_stages`` using an upsert operation and
            logs errors without raising them.
        """
        now = _current_ts()
        try:
            self.db.execute_query(
                """
                INSERT INTO task_stages (
                    stage_id, task_id,
                    stage_name, stage_number,
                    stage_status, stage_sub_name,
                    stage_message, updated_at
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
                    stage_data.get("number", 0),
                    stage_data.get("status", "Pending"),
                    stage_data.get("sub_name"),
                    stage_data.get("message"),
                    now,
                ],
            )
        except Exception as exc:
            logger.error("Failed to update stage '%s' for task %s: %s", stage_name, task_id, exc)

    def replace_stages(self, task_id: str, stages: Dict[str, Dict[str, Any]]) -> None:
        """Replace all stages for a task with the provided mapping.

        Parameters:
            task_id (str): Task identifier whose stages should be reset.
            stages (dict[str, dict]): Mapping of stage name to metadata.

        Side Effects:
            Deletes existing rows in ``task_stages`` for the task and re-inserts
            the provided entries in bulk.
        """

        now = _current_ts()

        if not stages:
            return

        # NOTE: This method is not atomic. The DELETE and INSERTs should be wrapped in a single transaction.
        self.db.execute_query_safe("DELETE FROM task_stages WHERE task_id = %s", [task_id])

        params_seq = [
            (
                f"{task_id}:{stage_name}",
                task_id,
                stage_name,
                stage_data.get("number", 0),
                stage_data.get("status", "Pending"),
                stage_data.get("sub_name"),
                stage_data.get("message"),
                now,
            )
            for stage_name, stage_data in stages.items()
        ]
        if params_seq:
            self.db.execute_many(
                """
                INSERT INTO task_stages (
                    stage_id, task_id,
                    stage_name, stage_number,
                    stage_status, stage_sub_name,
                    stage_message, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                params_seq,
            )

    def fetch_stages(self, task_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch persisted stages for a given task as a mapping.

        Parameters:
            task_id (str): Identifier whose stage rows should be retrieved.

        Returns:
            dict[str, dict]: Stage metadata keyed by stage name. Returns an empty
            dict when the query fails or the task has no recorded stages.
        """
        rows = self.db.fetch_query_safe(
            """
                SELECT stage_name, stage_number, stage_status, stage_sub_name, stage_message, updated_at
                FROM task_stages
                WHERE task_id = %s
                ORDER BY stage_number
                """,
            [task_id],
        )
        if not rows:
            logger.error(f"Failed to fetch stages for task {task_id}")
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


class TaskStorePyMysql(StageStore):
    """MySQL-backed task store using helper functions execute_query/fetch_query."""

    def __init__(self, db_data: Dict[str, str]) -> None:
        # Note: db connection is managed inside execute_query/fetch_query
        # self._lock = threading.Lock()
        """
        Initialize the task store and ensure the required database schema exists.

        Calls internal schema initialization to create the tasks table and any necessary indexes.
        """
        self.db = Database(db_data)
        self._init_schema()

    def _init_schema(self) -> None:
        """
        Ensure the tasks table and its indexes exist in the MySQL database.

        Creates the tasks table (with text-based JSON columns for broad MySQL compatibility) and ensures indexes on normalized_title, status, and created_at are present. Index creation is guarded for compatibility with MySQL versions that do not support CREATE INDEX IF NOT EXISTS. Logs a warning if schema initialization fails.
        """
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
        # ---
        self.db.execute_query_safe(ddl[0])
        self.db.execute_query_safe(ddl[1])
        # ---
        # Conditionally create indexes for maximum compatibility
        existing = self.db.fetch_query_safe(
            """
            SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tasks'
            """
        )
        existing_idx = {row["INDEX_NAME"] for row in existing}
        if "idx_tasks_norm" not in existing_idx:
            self.db.execute_query_safe("CREATE INDEX idx_tasks_norm ON tasks(normalized_title)")
        # ---
        if "idx_tasks_status" not in existing_idx:
            self.db.execute_query_safe("CREATE INDEX idx_tasks_status ON tasks(status)")
        # ---
        if "idx_tasks_created" not in existing_idx:
            self.db.execute_query_safe("CREATE INDEX idx_tasks_created ON tasks(created_at)")
        # ---
        existing_stage_idx = self.db.fetch_query_safe(
            """
            SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'task_stages'
            """
        )
        # ---
        existing_stage_idx_names = {row["INDEX_NAME"] for row in existing_stage_idx}
        if "idx_task_stages_task" not in existing_stage_idx_names:
            self.db.execute_query_safe("CREATE INDEX idx_task_stages_task ON task_stages(task_id, stage_number)")

    def create_task(
        self,
        task_id: str,
        title: str,
        status: str = "Pending",
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
        now = _current_ts()
        normalized_title = _normalize_title(title)
        # Application-level guard to ensure at most one active task per normalized_title.
        # with self._lock:
        try:
            # Check for an existing active task
            rows = self.db.fetch_query(
                """
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
                    WHERE normalized_title = %s AND status NOT IN (%s, %s)
                    ORDER BY created_at DESC
                    LIMIT 1
                ) AS t
                LEFT JOIN task_stages ts ON t.id = ts.task_id
                ORDER BY COALESCE(ts.stage_number, 0) ASC
                """,
                [normalized_title, *TERMINAL_STATUSES],
            )
            if rows:
                task_rows, stage_map = self._rows_to_tasks_with_stages(rows)
                existing_task_row = task_rows[0]
                existing_task = self._row_to_task(
                    existing_task_row,
                    stages=stage_map.get(existing_task_row["id"], {}),
                )
                raise TaskAlreadyExistsError(existing_task)

            # Insert new task
            self.db.execute_query(
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
        return self._row_to_task(task_row, stages=stage_map.get(task_row["id"], {}))

    def get_active_task_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent active task whose title matches the given title after trimming and casefold normalization.

        Parameters:
            title (str): Title to match; whitespace is stripped and casefolded before lookup.

        Returns:
            dict: Task dictionary with deserialized JSON fields and ISO-formatted timestamps, or `None` if no active task is found or an error occurs.
        """
        normalized_title = _normalize_title(title)
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
            FROM (
                SELECT * FROM tasks
                WHERE normalized_title = %s AND status NOT IN (%s, %s)
                ORDER BY created_at DESC
                LIMIT 1
            ) AS t
            LEFT JOIN task_stages ts ON t.id = ts.task_id
            ORDER BY COALESCE(ts.stage_number, 0) ASC
            """,
            [normalized_title, *TERMINAL_STATUSES],
        )
        if not rows:
            logger.error("Failed to get task")
            return None

        task_rows, stage_map = self._rows_to_tasks_with_stages(rows)
        if not task_rows:
            logger.error("Failed to get task")
            return None

        task_row = task_rows[0]
        return self._row_to_task(task_row, stages=stage_map.get(task_row["id"], {}))

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
            self.db.execute_query(
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
                    _current_ts(),
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

    def _row_to_task(
        self,
        row: Dict[str, Any],
        *,
        stages: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # row is a dict from pymysql DictCursor via fetch_query()
        """
        Convert a database row dictionary into a task dictionary suitable for application use.

        Parameters:
            row (Dict[str, Any]): A row returned from the database (pymysql DictCursor).
            stages (Optional[Dict[str, Dict[str, Any]]]): Optional pre-fetched stage mapping to attach
                to the returned task. When not provided, the stages will be loaded via ``fetch_stages``.

        Returns:
            Dict[str, Any]: Task dictionary with keys:
                - id: task identifier
                - title: original title
                - normalized_title: normalized title used for duplicate checks
                - status: task status
                - form: deserialized form payload or None
                - data: deserialized data payload or None
                - results: deserialized results payload or None
                - created_at: ISO 8601 timestamp string if available, otherwise string representation
                - updated_at: ISO 8601 timestamp string if available, otherwise string representation
                - stages: Mapping of stage names to stage details
        """
        if stages is None:
            stages = self.fetch_stages(row["id"])

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
            "stages": stages or {},
        }

    def _rows_to_tasks_with_stages(
        self, rows: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Dict[str, Any]]]]:
        """Split combined task/stage join rows into task rows and stage mapping.

        Parameters:
            rows (list[dict]): Result set from a join between ``tasks`` and
                ``task_stages``.

        Returns:
            tuple: ``(task_rows, stage_map)`` where ``task_rows`` is an ordered
            list of unique task dictionaries, and ``stage_map`` maps task IDs to a
            stage-name-to-metadata dictionary.
        """
        task_rows: Dict[str, Dict[str, Any]] = {}
        stage_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for row in rows:
            task_id = row["id"]

            if task_id not in task_rows:
                task_rows[task_id] = dict(row)

            stage_name = row.get("stage_name")
            if stage_name is None:
                continue

            updated_at = row.get("stage_updated_at")
            if hasattr(updated_at, "isoformat"):
                updated_str = updated_at.isoformat()
            else:
                updated_str = str(updated_at) if updated_at is not None else None

            task_stage_map = stage_map.setdefault(task_id, {})
            task_stage_map[stage_name] = {
                "number": row.get("stage_number"),
                "status": row.get("stage_status"),
                "sub_name": row.get("stage_sub_name"),
                "message": row.get("stage_message"),
                "updated_at": updated_str,
            }

        return list(task_rows.values()), stage_map

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
        """
        List tasks from the store with optional filtering, ordering, and pagination.

        Parameters:
            status (Optional[str]): A single status to filter by.
            statuses (Optional[Iterable[str]]): An iterable of statuses to filter by; combined with `status` when both are provided.
            order_by (str): Column to order results by; allowed values are "created_at", "updated_at", "title", and "status". Invalid values default to "created_at".
            descending (bool): If True, sort in descending order; otherwise sort ascending.
            limit (Optional[int]): Maximum number of rows to return.
            offset (Optional[int]): Number of rows to skip before returning results. If `offset` is provided without `limit`, an implementation-wide large limit is applied to allow offsetting.

        Returns:
            List[Dict[str, Any]]: A list of task dictionaries (as produced by `_row_to_task`) matching the query; returns an empty list on query failure.
        """
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

        base_sql = " ".join(query_parts)
        sql = f"""
            SELECT
                t.*,
                ts.stage_name AS stage_name,
                ts.stage_number AS stage_number,
                ts.stage_status AS stage_status,
                ts.stage_sub_name AS stage_sub_name,
                ts.stage_message AS stage_message,
                ts.updated_at AS stage_updated_at
            FROM ({base_sql}) AS t
            LEFT JOIN task_stages ts ON t.id = ts.task_id
            ORDER BY t.{order_column} {direction}, COALESCE(ts.stage_number, 0) ASC
        """

        rows = self.db.fetch_query_safe(sql, params)

        if not rows:
            logger.error("Failed to list tasks")
            return []

        task_rows, stage_map = self._rows_to_tasks_with_stages(rows)
        if not task_rows:
            logger.error("Failed to list tasks")
            return []

        tasks: List[Dict[str, Any]] = [
            self._row_to_task(task_row, stages=stage_map.get(task_row["id"], {}))
            for task_row in task_rows
        ]

        return tasks
