"""Application configuration helpers."""

from __future__ import annotations
from typing import Any
from .svg_db import fetch_query_safe


class Admins:
    def __init__(self) -> None:
        """
        Initialize the Admins class with an empty list to store admin usernames.
        """
        self.admins = []

    def list(self) -> list[Any | None]:
        # if self.admins: return self.admins
        # admins = [x.strip() for x in os.getenv("ADMINS", "").split(",") if x]
        rows = fetch_query_safe(
            """
            SELECT id, username, is_active, created_at, updated_at
            FROM admin_users
            ORDER BY id ASC
            """
        )

        self.admins = [row.get("username") for row in rows if row.get("is_active")]

        return self.admins

    def clear(self) -> None:
        self.admins = []

    def refresh(self) -> None:
        self.clear()
        self.list()


admins = Admins()
