import pymysql
from svg_config import db_data
# from . import Database
from .db_class import Database

db = Database(db_data)

def execute_query(sql_query: str, params: list = None):
    """
    Execute an SQL statement using the module-level database configuration and return its result.

    Parameters:
        sql_query (str): The SQL statement to execute.
        params (list, optional): Positional parameters for parameterized SQL; pass None if there are no parameters.

    Returns:
        result: For SELECT queries, a list of row dictionaries; for non-SELECT queries, an integer count of affected rows.
    """

    if params:
        results = db.execute_query(sql_query, params)
    else:
        results = db.execute_query(sql_query)

    return results


def fetch_query(sql_query: str, params: list = None) -> list:
    """
    Execute a SQL query using the module-level database configuration and return all fetched rows.

    Parameters:
        sql_query (str): The SQL statement to execute.
        params (list, optional): Sequence of parameters to bind into the query.

    Returns:
        list: All rows returned by the query as a list of dictionaries (empty list if no rows).
    """

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

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS task_stages (
            stage_id VARCHAR(255) PRIMARY KEY,
            task_id VARCHAR(64) NOT NULL,
            stage_name VARCHAR(255) NOT NULL,
            stage_number INT NOT NULL,
            stage_status VARCHAR(50) NOT NULL,
            stage_sub_name TEXT NULL,
            stage_message TEXT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT fk_task_stage_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            CONSTRAINT uq_task_stage UNIQUE (task_id, stage_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # Lookup/sort indexes
    execute_query("CREATE INDEX IF NOT EXISTS idx_tasks_norm ON tasks(normalized_title)")
    execute_query("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    execute_query("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
    execute_query("CREATE INDEX IF NOT EXISTS idx_task_stages_task ON task_stages(task_id, stage_number)")

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
