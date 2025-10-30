from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

# from .utils import DbUtils
# from .db_StageStore import StageStore
from .db_class import Database

logger = logging.getLogger(__name__)


class TasksListDB:  # (StageStore, DbUtils)

    def __init__(self, db : Database | None = None) -> None:
        self.db = db

    def create_base_sql(self, order_column, statuses, status, username, direction, limit, offset):

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

        if username:
            where_clauses.append("username = %s")
            params.append(username)

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append(f"ORDER BY {order_column} {direction}")

        if limit is not None:
            query_parts.append("LIMIT %s")
            params.append(limit)
        if offset is not None:
            if limit is None:
                query_parts.append("LIMIT 18446744073709551615")
            query_parts.append("OFFSET %s")
            params.append(offset)

        return query_parts, params

    def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        statuses: Optional[Iterable[str]] = None,
        order_by: str = "created_at",
        descending: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        username: Optional[str] = None,
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
        direction = "DESC" if descending else "ASC"

        query_parts, params = self.create_base_sql(order_column, statuses, status, username, direction, limit, offset)

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
            self._row_to_task(
                task_row,
                stages=stage_map.get(task_row["id"], {})  # or self.fetch_stages(task_row["id"])
            )
            for task_row in task_rows
        ]

        return tasks
