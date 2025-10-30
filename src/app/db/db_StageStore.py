from __future__ import annotations

import logging
from re import I
from typing import Any, Dict
# from .utils import DbUtils
from .db_class import Database

logger = logging.getLogger(__name__)


class StageStore:  # (DbUtils)
    """Utility mixin providing CRUD helpers for task stage persistence."""

    def __init__(self, db : Database | None = None) -> None:
        self.db = db

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
        now = self._current_ts()
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

    def update_stage_column(
        self,
        task_id: str,
        stage_name: str,
        column_name: str,
        column_value: Any,
    ) -> None:
        """
        Update a single column for a task stage (e.g., stage_message or stage_status).
        Only a fixed set of columns is allowed to prevent SQL injection.
        """
        # Allow-list permissible stage columns
        allowed_cols = {
            "stage_number",
            "stage_status",
            "stage_sub_name",
            "stage_message",
        }
        if column_name not in allowed_cols:
            logger.error(f"Illegal stage column: {column_name!r}")
            return

        now = self._current_ts()
        try:
            sql = (
                "UPDATE task_stages "
                f"SET {column_name} = %s, updated_at = %s "
                "WHERE stage_id = %s"
            )
            self.db.execute_query(
                sql,
                [column_value, now, f"{task_id}:{stage_name}"],
            )
        except Exception:
            logger.error("Failed to update stage '%s' for task %s", stage_name, task_id)

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
