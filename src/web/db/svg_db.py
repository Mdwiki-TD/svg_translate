
from svg_config import db_data
from . import Database

# from db import execute_query, fetch_query
# data = fetch_query(sql_query, params)
# execute_query(sql_query, params)


def execute_query(sql_query: str, params: list = None):
    db = Database(db_data)

    if params:
        results = db.execute_query(sql_query, params)
    else:
        results = db.execute_query(sql_query)

    return results


def fetch_query(sql_query: str, params: list = None) -> list:
    db = Database(db_data)

    if params:
        results = db.fetch_query(sql_query, params)
    else:
        results = db.fetch_query(sql_query)

    return results


def init_schema() -> None:
    # Create the main tasks table
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id VARCHAR(64) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            normalized_title VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            form_json JSON NULL,
            data_json JSON NULL,
            results_json JSON NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # Lookup/sort indexes
    execute_query("CREATE INDEX IF NOT EXISTS idx_tasks_norm ON tasks(normalized_title)")
    execute_query("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    execute_query("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")

    # Enforce at most one active task per normalized_title
    # MySQL does not support partial indexes directly; use a unique composite index with condition simulation.
    # Option 1: enforce via trigger or app logic.
    # Option 2 (MySQL 8.0+): use functional index with expression
    execute_query(
        """
        CREATE UNIQUE INDEX uq_active_title
        ON tasks(normalized_title, status)
        """
    )
