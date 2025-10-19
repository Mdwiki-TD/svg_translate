import pymysql
from svg_config import db_data
# from . import Database

# from db import execute_query, fetch_query
# data = fetch_query(sql_query, params)
# execute_query(sql_query, params)


class Database:
    def __init__(self, db_data):

        self.host = db_data['host']
        self.user = db_data['user']
        self.dbname = db_data['dbname']
        self.password = db_data['password']

        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.dbname,
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.MySQLError as e:
            print(f"Error connecting to the database: {e}")
            exit()

    def execute_query(self, sql_query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql_query, params)

            # Check if the query starts with "SELECT"
            if sql_query.upper().strip().startswith('SELECT'):
                result = cursor.fetchall()
                return result
            else:
                self.connection.commit()
                return cursor.rowcount

    def fetch_query(self, sql_query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql_query, params)

            result = cursor.fetchall()
            return result


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
