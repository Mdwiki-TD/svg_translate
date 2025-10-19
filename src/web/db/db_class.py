
import pymysql

# from svg_config import db_data


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
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)

                # Check if the query starts with "SELECT"
                if sql_query.upper().strip().startswith('SELECT'):
                    result = cursor.fetchall()
                    return result
                else:
                    self.connection.commit()
                    return cursor.rowcount

        except pymysql.MySQLError as e:
            print(f"SQL error: {e}<br>{sql_query}")
            return []

    def fetch_query(self, sql_query, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)

                result = cursor.fetchall()
                return result
        except pymysql.MySQLError as e:
            print(f"SQL error: {e}<br>{sql_query}")
            return []
