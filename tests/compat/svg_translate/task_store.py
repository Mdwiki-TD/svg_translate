"""Lightweight JSON-backed task store used by unit tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from src.web.db.task_store_pymysql import TaskAlreadyExistsError  # type: ignore
from src.web.db.utils import _normalize_title

TERMINAL_STATUSES = {"Completed", "Failed"}


class TaskStore:
    """Minimal task store implementation sufficient for compatibility tests."""

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            data = {}
        self._tasks: Dict[str, Dict[str, object]] = data.get("tasks", {})

    def _save(self) -> None:
        payload = {"tasks": self._tasks}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def close(self) -> None:  # pragma: no cover - included for API compatibility
        self._save()

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------
    def create_task(self, task_id: str, title: str, form: Optional[Dict[str, object]] = None) -> None:
        normalized = _normalize_title(title)
        existing = self.get_active_task_by_title(title)
        if existing and existing.get("status") not in TERMINAL_STATUSES:
            raise TaskAlreadyExistsError(existing)

        now = datetime.now(timezone.utc).isoformat()
        self._tasks[task_id] = {
            "id": task_id,
            "title": title,
            "normalized_title": normalized,
            "status": "Pending",
            "form": form or {},
            "data": {},
            "results": {},
            "stages": {},
            "created_at": now,
            "updated_at": now,
        }
        self._save()

    def update_status(self, task_id: str, status: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        task["status"] = status
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def update_data(self, task_id: str, data: Dict[str, object]) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        task.setdefault("data", {}).update(data)
        self._save()

    def update_results(self, task_id: str, results: Dict[str, object]) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        task["results"] = results
        self._save()

    def update_stage(self, task_id: str, stage_name: str, stage_data: Dict[str, object]) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        stages = task.setdefault("stages", {})
        entry = dict(stage_data)
        entry.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        stages[stage_name] = entry
        self._save()

    def replace_stages(self, task_id: str, stages: Dict[str, Dict[str, object]]) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        snapshot = {}
        for name, data in stages.items():
            entry = dict(data)
            entry.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
            snapshot[name] = entry
        task["stages"] = snapshot
        self._save()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_task(self, task_id: str) -> Optional[Dict[str, object]]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        result = json.loads(json.dumps(task))  # deep copy
        if "form" in result and result["form"] is None:
            result["form"] = {}
        return result

    def list_tasks(self, status: Optional[str] = None, order_by: str = "created_at", descending: bool = False):
        tasks = list(self._tasks.values())
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        reverse = descending
        tasks.sort(key=lambda t: t.get(order_by), reverse=reverse)
        return [json.loads(json.dumps(task)) for task in tasks]

    def get_active_task_by_title(self, title: str) -> Optional[Dict[str, object]]:
        normalized = _normalize_title(title)
        for task in self._tasks.values():
            if task.get("normalized_title") == normalized and task.get("status") not in TERMINAL_STATUSES:
                return json.loads(json.dumps(task))
        return None


__all__ = ["TaskStore", "TaskAlreadyExistsError"]
