from __future__ import annotations

import logging
from typing import Dict

from .db_class import Database

from .utils import DbUtils
from .db_TasksListDB import TasksListDB
from .db_StageStore import StageStore
from .db_CreateUpdate import CreateUpdateTask

logger = logging.getLogger(__name__)


class TaskStorePyMysql(CreateUpdateTask, StageStore, TasksListDB, DbUtils):
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
        super().__init__(self.db)

    def close(self) -> None:
        """Close the underlying database connection."""
        self.db.close()

    def __enter__(self) -> "TaskStorePyMysql":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()

    def _init_schema(self) -> None:
        """
        Ensure the tasks table and its indexes exist in the MySQL database.

        Creates the tasks table (with text-based JSON columns for broad MySQL compatibility) and
        ensures indexes on normalized_title, status, and created_at are present. Index creation is
        guarded for compatibility with MySQL versions that do not support CREATE INDEX IF NOT EXISTS.
        Logs a warning if schema initialization fails.
        """
        # Use TEXT for JSON fields for wider MySQL compatibility.
        # If your MySQL supports JSON type, you can switch to JSON.
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id VARCHAR(128) PRIMARY KEY,
                username TEXT NULL,
                title TEXT NOT NULL,
                normalized_title VARCHAR(512) NOT NULL,
                main_file VARCHAR(512) NULL,
                status VARCHAR(64) NOT NULL,
                form_json LONGTEXT NULL,
                data_json LONGTEXT NULL,
                results_json LONGTEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
