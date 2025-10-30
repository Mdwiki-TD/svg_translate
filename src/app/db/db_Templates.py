
from __future__ import annotations

import logging
import pymysql
from dataclasses import dataclass
from typing import Any, List
from . import Database

logger = logging.getLogger(__name__)


@dataclass
class TemplateRecord:
    """Representation of a template."""

    id: int
    title: str
    main_file: bool
    created_at: Any | None = None
    updated_at: Any | None = None


class TemplatesDB:
    """MySQL-backed"""

    def __init__(self, db_data: dict[str, Any]):
        self.db = Database(db_data)
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.db.execute_query_safe(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL UNIQUE,
                main_file VARCHAR(255) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    def _row_to_record(self, row: dict[str, Any]) -> TemplateRecord:
        return TemplateRecord(
            id=int(row["id"]),
            title=row["title"],
            main_file=row.get("main_file"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _fetch_by_title(self, title: str) -> TemplateRecord:
        rows = self.db.fetch_query_safe(
            """
            SELECT id, title, main_file, created_at, updated_at
            FROM templates
            WHERE title = %s
            """,
            (title,),
        )
        if not rows:
            raise LookupError(f"Template {title!r} was not found")
        return self._row_to_record(rows[0])

    def list(self) -> List[TemplateRecord]:
        rows = self.db.fetch_query_safe(
            """
            SELECT id, title, main_file, created_at, updated_at
            FROM templates
            ORDER BY id ASC
            """
        )
        return [self._row_to_record(row) for row in rows]

    def add(self, title: str, main_file: str) -> TemplateRecord:
        title = title.strip()
        main_file = main_file.strip()
        if not title:
            raise ValueError("Title is required")

        if not main_file:
            raise ValueError("Main file is required")

        try:
            # Use execute_query to allow exception to propagate
            self.db.execute_query(
                """
                INSERT INTO templates (title, main_file) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    main_file = VALUES(main_file)
                """,
                (title, main_file),
            )
        except pymysql.err.IntegrityError:
            # This assumes a UNIQUE constraint on the title column
            raise ValueError(f"Template '{title}' already exists") from None

        return self._fetch_by_title(title)

    def add_main_file(self, template_id: int, main_file: str) -> TemplateRecord:
        _ = self._fetch_by_id(template_id)
        self.db.execute_query_safe(
            "UPDATE templates SET main_file = %s WHERE id = %s",
            (main_file, template_id),
        )
        return self._fetch_by_id(template_id)

    def delete(self, template_id: int) -> TemplateRecord:
        record = self._fetch_by_id(template_id)
        self.db.execute_query_safe(
            "DELETE FROM templates WHERE id = %s",
            (template_id,),
        )
        return record


__all__ = [
    "TemplatesDB",
    "TemplateRecord",
]
