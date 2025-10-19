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
