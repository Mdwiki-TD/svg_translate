
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, List, Protocol

logger = logging.getLogger(__name__)


@dataclass
class CoordinatorRecord:
    """Representation of a coordinator/admin account."""

    id: int
    username: str
    is_active: bool
    created_at: Any | None = None
    updated_at: Any | None = None


class CoordinatorStore(Protocol):
    """Minimal persistence interface for coordinator records."""

    def seed(self, usernames: Iterable[str]) -> None:
        """Ensure the provided usernames exist as active coordinators."""

    def list(self) -> List[CoordinatorRecord]:
        """Return all known coordinators ordered by identifier."""

    def add(self, username: str) -> CoordinatorRecord:
        """Persist a new coordinator and return the created record."""

    def set_active(self, coordinator_id: int, is_active: bool) -> CoordinatorRecord:
        """Toggle the active flag for a coordinator and return the updated record."""

    def delete(self, coordinator_id: int) -> CoordinatorRecord:
        """Remove a coordinator and return the deleted record."""


# from .admin_service_utils import CoordinatorStore, CoordinatorRecord
__all__ = [
    "CoordinatorStore",
    "CoordinatorRecord",
]
