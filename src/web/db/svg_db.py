import pymysql
from svg_config import db_data
# from . import Database

# from db import execute_query, fetch_query
# data = fetch_query(sql_query, params)
# execute_query(sql_query, params)


class Database:
    def __init__(self, db_data):

        """
        Initialize the Database with connection parameters and establish a MySQL connection.
        
        Parameters:
            db_data (dict): Mapping with connection keys:
                - 'host': database host name or IP
                - 'user': database username
                - 'dbname': database name
                - 'password': database password
        
        Behavior:
            Stores the provided connection parameters on the instance and attempts to open a MySQL connection. If the connection attempt fails, prints an error message and exits the process.
        """
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
        """
        Execute an SQL statement and return query results or affected row count.
        
        Parameters:
            sql_query (str): The SQL statement to execute. Leading whitespace and case are ignored when determining query type.
            params (tuple|list|dict, optional): Parameters to bind to the query, if any.
        
        Returns:
            list[dict]: For SELECT queries, a list of rows (cursor dicts) fetched from the database.
            int: For non-SELECT queries, the number of rows affected; the change is committed to the database.
        """
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
        """
        Execute the given SQL query and return all fetched rows.
        
        Parameters:
            sql_query (str): The SQL statement to execute.
            params (sequence|dict|None): Optional parameters to bind into the query.
        
        Returns:
            list[dict]: All rows returned by the query; each row is a dict keyed by column name.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql_query, params)

            result = cursor.fetchall()
            return result


def execute_query(sql_query: str, params: list = None):
    """
    Execute an SQL statement using the module-level database configuration and return its result.
    
    Parameters:
        sql_query (str): The SQL statement to execute.
        params (list, optional): Positional parameters for parameterized SQL; pass None if there are no parameters.
    
    Returns:
        result: For SELECT queries, a list of row dictionaries; for non-SELECT queries, an integer count of affected rows.
    """
    db = Database(db_data)

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
    db = Database(db_data)

    if params:
        results = db.fetch_query(sql_query, params)
    else:
        results = db.fetch_query(sql_query)

    return results


def init_schema() -> None:
    # Create the main tasks table
    """
    Create the database schema required for task storage and indexing.
    
    Creates the tasks table if it does not exist with columns for id, title, normalized_title, status, JSON payloads, and timestamps. Also creates lookup and sorting indexes on normalized_title, status, and created_at, and adds a unique composite index on (normalized_title, status) intended to limit duplicate active tasks (note: this composite index is not a true partial index; enforcement of "at most one active task" may require application logic or database mechanisms beyond a standard unique index).
    """
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