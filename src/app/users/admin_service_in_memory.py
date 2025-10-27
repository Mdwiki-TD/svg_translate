
from __future__ import annotations

import logging
from typing import Iterable, List, Optional
from .admin_service_utils import CoordinatorStore, CoordinatorRecord

logger = logging.getLogger(__name__)


class InMemoryCoordinatorStore(CoordinatorStore):
    """Simple in-memory coordinator store used for tests or no-DB setups."""

    def __init__(self, initial: Optional[Iterable[str]] = None) -> None:
        self._records: list[CoordinatorRecord] = []
        self._next_id = 1
        if initial:
            self.seed(initial)

    def seed(self, usernames: Iterable[str]) -> None:
        for username in usernames:
            username = username.strip() if username else ""
            if not username:
                continue
            if any(rec.username == username for rec in self._records):
                continue
            self._records.append(
                CoordinatorRecord(
                    id=self._consume_id(),
                    username=username,
                    is_active=True,
                )
            )

    def _consume_id(self) -> int:
        current = self._next_id
        self._next_id += 1
        return current

    def list(self) -> List[CoordinatorRecord]:
        return [CoordinatorRecord(**rec.__dict__) for rec in self._records]

    def add(self, username: str) -> CoordinatorRecord:
        username = username.strip()
        if not username:
            raise ValueError("Username is required")
        if any(rec.username == username for rec in self._records):
            raise ValueError(f"Coordinator '{username}' already exists")
        record = CoordinatorRecord(
            id=self._consume_id(),
            username=username,
            is_active=True,
        )
        self._records.append(record)
        return CoordinatorRecord(**record.__dict__)

    def _get_index(self, coordinator_id: int) -> int:
        for index, record in enumerate(self._records):
            if record.id == coordinator_id:
                return index
        raise LookupError(f"Coordinator id {coordinator_id} was not found")

    def set_active(self, coordinator_id: int, is_active: bool) -> CoordinatorRecord:
        index = self._get_index(coordinator_id)
        self._records[index].is_active = bool(is_active)
        return CoordinatorRecord(**self._records[index].__dict__)

    def delete(self, coordinator_id: int) -> CoordinatorRecord:
        index = self._get_index(coordinator_id)
        record = self._records.pop(index)
        return CoordinatorRecord(**record.__dict__)


__all__ = [
    "InMemoryCoordinatorStore",
]
