
import json
import datetime
from typing import Any, Dict, List, Optional, Tuple


class DbUtils:
    def __init__(self):
        pass

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
        return {
            "id": row["id"],
            "username": row.get("username", ""),
            "title": row["title"],
            "normalized_title": row["normalized_title"],
            "status": row["status"],
            "form": self._deserialize(row.get("form_json")),
            "data": self._deserialize(row.get("data_json")),
            "main_file": row.get("main_file", ""),
            "results": self._deserialize(row.get("results_json")),
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
            "stages": stages or {},
        }

    def _serialize(self, value: Any) -> Optional[str]:
        """
        Serialize a Python value to a JSON string suitable for storage, or return None for missing values.

        Parameters:
            value (Any): The Python value to serialize; if `None`, no serialization is performed.

        Returns:
            Optional[str]: JSON string of `value` with Unicode preserved (`ensure_ascii=False`), or `None` if `value` is `None`.
        """
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def _deserialize(self, value: Optional[str]) -> Any:
        """
        Deserialize a JSON-formatted string into a Python object.

        Parameters:
            value (Optional[str]): A JSON-formatted string, or None.

        Returns:
            The Python object produced by parsing `value`, or `None` if `value` is `None`.
        """
        if value is None:
            return None
        return json.loads(value)

    def _current_ts(self) -> str:
        # Store in UTC. MySQL DATETIME has no TZ; keep application-level UTC.
        """
        Return the current UTC timestamp formatted for MySQL DATETIME.

        Returns:
            A string of the current UTC time in the format "YYYY-MM-DD HH:MM:SS".
        """
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _normalize_title(self, title: str) -> str:
        """
        Normalize a title for duplicate detection.

        Returns:
            normalized (str): The title with surrounding whitespace removed and casefold applied.
        """
        title = title.replace("_", " ")
        return title.strip().casefold()
