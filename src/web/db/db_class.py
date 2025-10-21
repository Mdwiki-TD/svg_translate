
import logging
import pymysql


logger = logging.getLogger(__name__)


class Database:
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
            print(f"Error connecting to the database: {e}")
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
        with self.connection.cursor() as cursor:
            cursor.execute(sql_query, params)

            self.connection.commit()
            return cursor.rowcount

    def fetch_query(self, sql_query, params=None):
        """
        Execute a SQL query and return all fetched rows.

        Parameters:
            sql_query (str): The SQL statement to execute.
            params (tuple|dict|None): Optional parameters for a parameterized query.

        Returns:
            list: A list of rows (dictionaries when using a DictCursor). Returns an empty list if a SQL error occurs.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql_query, params)

            result = cursor.fetchall()
            return result

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
            print(f"execute_many - SQL error: {e}<br>{sql_query}")
            return 0

    def fetch_query_safe(self, sql_query, params=None):
        try:
            return self.fetch_query(sql_query, params)
        except pymysql.MySQLError as e:
            print(f"fetch_query - SQL error: {e}<br>{sql_query}, params:")
            print(params)
            return []

    def execute_query_safe(self, sql_query, params=None):
        try:
            return self.execute_query(sql_query, params)

        except pymysql.MySQLError as e:
            print(f"execute_query - SQL error: {e}<br>{sql_query}, params:")
            print(params)
            return 0
