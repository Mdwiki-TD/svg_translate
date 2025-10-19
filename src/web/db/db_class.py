
import pymysql

# from db_class import Database


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
        Execute a SQL query and return fetched rows for SELECT statements or the number of affected rows for other statements.

        Parameters:
            sql_query (str): SQL statement to execute.
            params (tuple|dict|None): Optional parameters to bind into the query.

        Returns:
            list[dict] | int: For SELECT queries, a list of result rows (each row as a dict). For non-SELECT queries, the number of affected rows. On SQL error, returns an empty list.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)

                self.connection.commit()
                return cursor.rowcount

        except pymysql.MySQLError as e:
            print(f"SQL error: {e}<br>{sql_query}")
            return []

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
        except pymysql.MySQLError as e:
            print(f"SQL error: {e}<br>{sql_query}")
            return []
