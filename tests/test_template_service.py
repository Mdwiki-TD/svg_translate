"""Unit tests for template_service module."""
from __future__ import annotations

import logging
from typing import Any, Iterable

import pymysql
import pytest

from src.app import template_service


class FakeDatabase:
    """Lightweight stub that mimics the Database helper using in-memory rows."""

    def __init__(self, _db_data: dict[str, Any]):
        self._rows: list[dict[str, Any]] = []
        self._next_id = 1

    def _normalize(self, sql: str) -> str:
        return " ".join(sql.strip().split()).lower()

    def _row_dict(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "main_file": row.get("main_file"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def execute_query(self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None) -> int:
        del timeout_override
        params = tuple(params or ())
        normalized = self._normalize(sql)

        if normalized.startswith("create table if not exists templates"):
            return 0

        if normalized.startswith("insert into templates") and "on duplicate key" not in normalized:
            title, main_file = params
            if any(row["title"] == title for row in self._rows):
                raise pymysql.err.IntegrityError(1062, "Duplicate entry")

            row = {
                "id": self._next_id,
                "title": title,
                "main_file": main_file,
                "created_at": None,
                "updated_at": None,
            }
            self._rows.append(row)
            self._next_id += 1
            return 1

        if "on duplicate key update" in normalized:
            title, main_file = params
            for row in self._rows:
                if row["title"] == title:
                    row["main_file"] = main_file
                    return 1
            # Not found, insert new
            row = {
                "id": self._next_id,
                "title": title,
                "main_file": main_file,
                "created_at": None,
                "updated_at": None,
            }
            self._rows.append(row)
            self._next_id += 1
            return 1

        if normalized.startswith("update templates"):
            title, main_file, template_id = params
            for row in self._rows:
                if row["id"] == template_id:
                    row["title"] = title
                    row["main_file"] = main_file
                    return 1
            return 0

        if normalized.startswith("delete from templates"):
            template_id = params[0]
            before = len(self._rows)
            self._rows = [row for row in self._rows if row["id"] != template_id]
            return 1 if len(self._rows) != before else 0

        raise NotImplementedError(sql)

    def execute_query_safe(self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None) -> int:
        try:
            return self.execute_query(sql, params, timeout_override=timeout_override)
        except pymysql.MySQLError:
            return 0

    def fetch_query(
        self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None
    ) -> list[dict[str, Any]]:
        del timeout_override
        params = tuple(params or ())
        normalized = self._normalize(sql)

        if "from templates" not in normalized:
            raise NotImplementedError(sql)

        if "where id = %s" in normalized:
            template_id = params[0]
            for row in self._rows:
                if row["id"] == template_id:
                    return [self._row_dict(row)]
            return []

        if "where title = %s" in normalized:
            title = params[0]
            for row in self._rows:
                if row["title"] == title:
                    return [self._row_dict(row)]
            return []

        if "order by id asc" in normalized:
            return [self._row_dict(row) for row in sorted(self._rows, key=lambda row: row["id"])]

        raise NotImplementedError(sql)

    def fetch_query_safe(
        self, sql: str, params: Iterable[Any] | None = None, *, timeout_override: float | None = None
    ) -> list[dict[str, Any]]:
        try:
            return self.fetch_query(sql, params, timeout_override=timeout_override)
        except pymysql.MySQLError:
            return []


@pytest.fixture
def mock_templates_store(monkeypatch: pytest.MonkeyPatch):
    """Create a mock TemplatesDB with FakeDatabase."""
    monkeypatch.setattr("src.app.db.db_Templates.Database", FakeDatabase)
    monkeypatch.setattr("src.app.template_service.has_db_config", lambda: True)
    
    # Reset the global store
    template_service._TEMPLATE_STORE = None
    
    yield
    
    # Clean up
    template_service._TEMPLATE_STORE = None


def test_get_templates_db_requires_config(monkeypatch: pytest.MonkeyPatch):
    """Test that get_templates_db raises when no database config is available."""
    template_service._TEMPLATE_STORE = None
    monkeypatch.setattr("src.app.template_service.has_db_config", lambda: False)
    
    with pytest.raises(RuntimeError, match="Template administration requires database configuration"):
        template_service.get_templates_db()


def test_get_templates_db_caches_store(_mock_templates_store):
    """Test that get_templates_db caches the store instance."""
    store1 = template_service.get_templates_db()
    store2 = template_service.get_templates_db()
    
    assert store1 is store2


def test_list_templates_empty(_mock_templates_store):
    """Test listing templates when none exist."""
    templates = template_service.list_templates()
    assert templates == []


def test_add_template_success(_mock_templates_store):
    """Test successfully adding a template."""
    record = template_service.add_template("Test Template", "test.svg")
    
    assert record.title == "Test Template"
    assert record.main_file == "test.svg"
    assert record.id > 0


def test_add_template_duplicate_raises_value_error(_mock_templates_store):
    """Test that adding a duplicate template raises ValueError."""
    template_service.add_template("Duplicate", "file1.svg")
    
    with pytest.raises(ValueError, match="Template 'Duplicate' already exists"):
        template_service.add_template("Duplicate", "file2.svg")


def test_add_template_empty_title_raises_value_error(_mock_templates_store):
    """Test that adding a template with empty title raises ValueError."""
    with pytest.raises(ValueError, match="Title is required"):
        template_service.add_template("", "file.svg")


def test_list_templates_returns_all(_mock_templates_store):
    """Test listing all templates."""
    template_service.add_template("Template 1", "file1.svg")
    template_service.add_template("Template 2", "file2.svg")
    template_service.add_template("Template 3", "file3.svg")
    
    templates = template_service.list_templates()
    
    assert len(templates) == 3
    assert templates[0].title == "Template 1"
    assert templates[1].title == "Template 2"
    assert templates[2].title == "Template 3"


def test_update_template_success(_mock_templates_store):
    """Test successfully updating a template."""
    record = template_service.add_template("Original", "original.svg")
    
    updated = template_service.update_template(record.id, "Updated", "updated.svg")
    
    assert updated.id == record.id
    assert updated.title == "Updated"
    assert updated.main_file == "updated.svg"


def test_update_template_not_found_raises_lookup_error(_mock_templates_store):
    """Test that updating a non-existent template raises LookupError."""
    with pytest.raises(LookupError, match="Template id 999 was not found"):
        template_service.update_template(999, "Title", "file.svg")


def test_delete_template_success(_mock_templates_store):
    """Test successfully deleting a template."""
    record = template_service.add_template("To Delete", "delete.svg")
    
    deleted = template_service.delete_template(record.id)
    
    assert deleted.title == "To Delete"
    assert len(template_service.list_templates()) == 0


def test_delete_template_not_found_raises_lookup_error(_mock_templates_store):
    """Test that deleting a non-existent template raises LookupError."""
    with pytest.raises(LookupError, match="Template id 999 was not found"):
        template_service.delete_template(999)


def test_add_or_update_template_adds_new(_mock_templates_store):
    """Test add_or_update creates a new template if it doesn't exist."""
    record = template_service.add_or_update_template("New Template", "new.svg")
    
    assert record.title == "New Template"
    assert record.main_file == "new.svg"
    assert record.id > 0


def test_add_or_update_template_updates_existing(_mock_templates_store):
    """Test add_or_update updates an existing template."""
    original = template_service.add_template("Existing", "old.svg")
    
    updated = template_service.add_or_update_template("Existing", "new.svg")
    
    assert updated.id == original.id
    assert updated.title == "Existing"
    assert updated.main_file == "new.svg"


def test_add_or_update_template_with_empty_title(_mock_templates_store, caplog):
    """Test add_or_update with empty title logs error but doesn't raise."""
    with caplog.at_level(logging.ERROR):
        # This should succeed despite empty title due to safe query
        template_service.add_or_update_template("", "file.svg")
        
        # Check that error was logged
        assert "Title is required for add_or_update" in caplog.text


def test_template_record_dataclass_with_none_main_file(_mock_templates_store):
    """Test TemplateRecord with None main_file (type annotation change)."""
    record = template_service.add_template("No Main File", "")
    
    assert record.title == "No Main File"
    assert isinstance(record.main_file, str)


def test_module_exports_all_functions():
    """Test that all expected functions are exported in __all__."""
    assert "get_templates_db" in template_service.__all__
    assert "TemplateRecord" in template_service.__all__
    assert "TemplatesDB" in template_service.__all__
    assert "list_templates" in template_service.__all__
    assert "add_or_update_template" in template_service.__all__
    assert "add_template" in template_service.__all__
    assert "update_template" in template_service.__all__
    assert "delete_template" in template_service.__all__


def test_logger_uses_svg_translate_name():
    """Test that the logger uses 'svg_translate' instead of __name__."""
    assert template_service.logger.name == "svg_translate"