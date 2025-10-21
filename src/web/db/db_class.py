
import logging
import pymysql


logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around a PyMySQL connection with convenience helpers."""

    def __init__(self, db_data):
        """
        Initialize the Database instance and establish a MySQL connection using credentials from db_data.

        Parameters:
            db_data (dict): Dictionary containing connection credentials with keys
                'host', 'user', 'dbname', and 'password'. On successful connection,
                stores these values as instance attributes and sets `self.connection`
                to a pymysql connection using a DictCursor. On connection failure,
                prints an error message and exits the process.
        """

        self.host = db_data['host']
        self.dbname = db_data['dbname']

        self.user = db_data['user']
        self.password = db_data['password']

        if not db_data.get("db_connect_file"):
            self.credentials = {
                'user': self.user,
                'password': self.password
            }
        else:
            self.credentials = {'read_default_file': db_data.get("db_connect_file")}

        try:
            self.connection = pymysql.connect(
                host=self.host,
                database=self.dbname,
                connect_timeout=5,
                read_timeout=10,
                write_timeout=10,
                charset="utf8mb4",
                init_command="SET time_zone = '+00:00'",
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
                **self.credentials
            )
        except pymysql.MySQLError as e:
            logger.debug(f"Error connecting to the database: {e}")
            exit()

    def execute_query(self, sql_query, params=None):
        """
        Execute a SQL query and return fetched rows for SELECT statements or the number of affected rows for other statements.

        Parameters:
            sql_query (str): SQL statement to execute.
            params (tuple|dict|None): Optional parameters to bind into the query.

        Returns:
            list[dict] | int: For SELECT queries, a list of result rows (each row as a dict). For non-SELECT queries, the number of affected rows. On SQL error, returns an empty list.
        """
        statement = (sql_query or "").strip().lower()
        is_select = statement.startswith("select")

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)

                if is_select:
                    return cursor.fetchall()

                self.connection.commit()
                return cursor.rowcount

        except pymysql.MySQLError as exc:
            logger.debug(f"execute_query - SQL error: {exc}<br>{sql_query}, params:")
            logger.debug(params)
            return [] if is_select else 0

    def fetch_query(self, sql_query, params=None):
        """
        Execute a SQL query and return all fetched rows.

        Parameters:
            sql_query (str): The SQL statement to execute.
            params (tuple|dict|None): Optional parameters for a parameterized query.

        Returns:
            list: A list of rows (dictionaries when using a DictCursor). Returns an empty list if a SQL error occurs.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)

                result = cursor.fetchall()
                return result

        except pymysql.MySQLError as exc:
            logger.debug(f"fetch_query - SQL error: {exc}<br>{sql_query}, params:")
            logger.debug(params)
            return []

    def execute_many(self, sql_query: str, params_seq, batch_size: int = 1000):
        """
        Bulk-execute a single SQL statement with many parameter sets.

        Args:
            sql_query: Single SQL statement (no multiple statements).
            params_seq: Iterable of tuple/dict parameters (e.g., list[tuple]).
            batch_size: How many rows per batch for executemany.

        Returns:
            int: Total affected rows across all batches. On SQL error, returns 0.
        """
        if not params_seq:
            return 0

        total = 0
        try:
            with self.connection.cursor() as cursor:
                # Process in batches to avoid packet/lock issues
                batch = []
                for p in params_seq:
                    batch.append(p)
                    if len(batch) >= batch_size:
                        cursor.executemany(sql_query, batch)
                        total += cursor.rowcount
                        batch.clear()
                if batch:
                    cursor.executemany(sql_query, batch)
                    total += cursor.rowcount

            self.connection.commit()
            return total

        except pymysql.MySQLError as e:
            # Roll back the whole unit of work to keep atomicity
            try:
                self.connection.rollback()
            except Exception:
                pass
            logger.debug(f"execute_many - SQL error: {e}<br>{sql_query}")
            return 0

    def fetch_query_safe(self, sql_query, params=None):
        """Return all rows for a query while converting SQL failures into logs.

        Parameters:
            sql_query (str): SQL statement to execute.
            params (tuple|dict|None): Optional parameters for the query.

        Returns:
            list[dict]: Query results when successful; otherwise an empty list if
            an exception is raised.
        """
        try:
            return self.fetch_query(sql_query, params)
        except pymysql.MySQLError as e:
            logger.error("event=db_fetch_failed sql=%s error=%s", sql_query, e)
            logger.debug(f"fetch_query - SQL error: {e}<br>{sql_query}, params:")
            logger.debug(params)
            return []

    def execute_query_safe(self, sql_query, params=None):
        """Execute a modifying statement while swallowing PyMySQL exceptions.

        Parameters:
            sql_query (str): SQL statement to execute.
            params (tuple|dict|None): Optional parameters for the query.

        Returns:
            int: Number of affected rows for success; ``0`` when an exception is
            encountered.
        """
        try:
            return self.execute_query(sql_query, params)

        except pymysql.MySQLError as e:
            logger.debug(f"execute_query - SQL error: {e}<br>{sql_query}, params:")
            logger.debug(params)
            statement = (sql_query or "").strip().lower()
            return [] if statement.startswith("select") else 0
