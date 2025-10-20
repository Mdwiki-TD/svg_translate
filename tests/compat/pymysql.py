class MySQLError(Exception):
    pass

class cursors:
    DictCursor = object

def connect(*args, **kwargs):  # pragma: no cover - stub
    raise MySQLError("pymysql stub does not provide connectivity")
