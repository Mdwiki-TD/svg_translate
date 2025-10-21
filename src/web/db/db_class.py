from __future__ import annotations

import logging
import threading
import random
import time
from typing import Any, Iterable, Sequence

import pymysql


logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around a PyMySQL connection with convenience helpers."""

    RETRYABLE_ERROR_CODES = {2006, 2013, 2014, 2017, 2018, 2055}
    MAX_RETRIES = 3
    BASE_BACKOFF = 0.2

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
        self._lock = threading.RLock()
        self.connection: Any | None = None

        try:
            self._connect()
        except pymysql.MySQLError as exc:  # pragma: no cover - defensive
            logger.error("event=db_connect_failed host=%s db=%s", self.host, self.dbname)
            logger.debug(f"Error connecting to the database: {exc}")
            raise

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def _connect(self) -> None:
        """Establish a new PyMySQL connection and store it on ``self``."""
        with self._lock:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.dbname,
                connect_timeout=5,
                read_timeout=10,
                write_timeout=10,
                charset="utf8mb4",
                init_command="SET time_zone = '+00:00'",
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
            )

    def _ensure_connection(self) -> None:
        """Ensure the current connection is alive, reconnecting as needed."""
        with self._lock:
            if self.connection is None:
                self._connect()
                return

            try:
                self.connection.ping(reconnect=True)
            except (pymysql.err.OperationalError, pymysql.err.InterfaceError):
                self._close_connection()
                self._connect()

    def _close_connection(self) -> None:
        with self._lock:
            if self.connection is not None:
                try:
                    self.connection.close()
                except Exception:  # pragma: no cover - best effort cleanup
                    pass
                finally:
                    self.connection = None

    # ------------------------------------------------------------------
    # Retry utilities
    # ------------------------------------------------------------------
    def _should_retry(self, exc: BaseException) -> bool:
        if isinstance(exc, (pymysql.err.OperationalError, pymysql.err.InterfaceError)):
            try:
                code = exc.args[0]
            except (IndexError, TypeError):
                return False
            return code in self.RETRYABLE_ERROR_CODES
        return False

    def _compute_backoff(self, attempt: int) -> float:
        return self.BASE_BACKOFF * (2 ** (attempt - 1)) + random.uniform(0, 0.1)

    def _log_retry(self, event: str, attempt: int, exc: BaseException, elapsed_ms: int) -> None:
        code = exc.args[0] if getattr(exc, "args", None) else None
        logger.debug(
            "event=%s attempt=%s code=%s elapsed_ms=%s", event, attempt, code, elapsed_ms
        )

    def _rollback_if_needed(self) -> None:
        with self._lock:
            if self.connection is None:
                return
            try:
                autocommit = self.connection.get_autocommit()  # type: ignore[attr-defined]
            except AttributeError:  # pragma: no cover - PyMySQL always exposes it
                autocommit = True
            if not autocommit:
                try:
                    self.connection.rollback()
                except Exception:  # pragma: no cover - defensive cleanup
                    pass

    def _execute_with_retry(
        self,
        operation,
        sql_query: str,
        params: Any,
        *,
        timeout_override: float | None = None,
    ):
        last_exc: BaseException | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            start = time.monotonic()
            try:
                self._ensure_connection()
                assert self.connection is not None  # for type checkers
                with self._lock:
                    cursor = self.connection.cursor()
                    try:
                        if timeout_override is not None:
                            self._set_query_timeout(cursor, timeout_override)
                        result = operation(cursor, sql_query, params)
                        return result
                    finally:
                        if timeout_override is not None:
                            self._reset_query_timeout(cursor)
                        cursor.close()
            except Exception as exc:  # noqa: PERF203 - retries require broad catch
                elapsed_ms = int((time.monotonic() - start) * 1000)
                if self._should_retry(exc) and attempt < self.MAX_RETRIES:
                    self._log_retry("db_retry", attempt, exc, elapsed_ms)
                    self._rollback_if_needed()
                    self._close_connection()
                    time.sleep(self._compute_backoff(attempt))
                    last_exc = exc
                    continue

                if isinstance(exc, pymysql.MySQLError):
                    self._log_retry("db_retry_failed", attempt, exc, elapsed_ms)
                self._rollback_if_needed()
                last_exc = exc
                break

        assert last_exc is not None  # for mypy
        raise last_exc

    # ------------------------------------------------------------------
    # Timeout helpers
    # ------------------------------------------------------------------
    def _set_query_timeout(self, cursor, timeout_override: float) -> None:
        milliseconds = max(int(timeout_override * 1000), 1)
        try:
            cursor.execute("SET SESSION MAX_EXECUTION_TIME=%s", (milliseconds,))
        except pymysql.MySQLError:
            logger.warning("event=db_set_timeout_failed timeout_ms=%s", milliseconds)

    def _reset_query_timeout(self, cursor) -> None:
        try:
            cursor.execute("SET SESSION MAX_EXECUTION_TIME=0")
        except pymysql.MySQLError:
            logger.warning("event=db_reset_timeout_failed")

    def _maybe_commit(self) -> None:
        if self.connection is None:
            return
        try:
            autocommit = self.connection.get_autocommit()  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover - PyMySQL always exposes it
            autocommit = True
        if not autocommit:
            self.connection.commit()

    def execute_query(
        self,
        sql_query: str,
        params: Any = None,
        *,
        timeout_override: float | None = None,
    ):
        """Execute a statement and return rows for SELECTs or rowcount for writes."""
        # TODO The new execute_query only commits when cursor.description is falsy. Statements that both modify data and produce a result set—such as stored procedures or INSERT/UPDATE … RETURNING in MySQL 8—set cursor.description, so this branch will fetch rows and return without ever calling _maybe_commit() when autocommit is disabled. Prior to this change execute_query always issued a commit, so these writes would persist. With the new logic those operations will leave the transaction uncommitted and silently lose data until the caller commits manually. Consider committing for any non‑SELECT statement (e.g. based on the SQL verb) even if it yields rows.

        def _op(cursor, sql, op_params):
            cursor.execute(sql, op_params)
            if cursor.description:
                return cursor.fetchall()
            self._maybe_commit()
            return cursor.rowcount

        return self._execute_with_retry(
            _op,
            sql_query,
            params,
            timeout_override=timeout_override,
        )

    def fetch_query(
        self,
        sql_query: str,
        params: Any = None,
        *,
        timeout_override: float | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and return all fetched rows as dictionaries."""

        def _op(cursor, sql, op_params):
            cursor.execute(sql, op_params)
            return cursor.fetchall()

        result = self._execute_with_retry(
            _op,
            sql_query,
            params,
            timeout_override=timeout_override,
        )
        return list(result or [])

    def execute_many(
        self,
        sql_query: str,
        params_seq: Iterable[Any],
        batch_size: int = 1000,
        *,
        timeout_override: float | None = None,
    ) -> int:
        """Bulk-execute a SQL statement with retry and chunk splitting."""

        params_list = list(params_seq)
        if not params_list:
            return 0

        def _op(cursor, sql, _params_list):
            return self._execute_many_batches(cursor, sql, params_list, batch_size)

        result = self._execute_with_retry(
            _op,
            sql_query,
            params_list,
            timeout_override=timeout_override,
        )
        self._maybe_commit()
        return int(result)

    def _execute_many_batches(
        self,
        cursor,
        sql_query: str,
        params_list: Sequence[Any],
        batch_size: int,
    ) -> int:
        total = 0
        index = 0
        while index < len(params_list):
            batch = params_list[index : index + batch_size]
            total += self._execute_many_batch(cursor, sql_query, batch)
            index += batch_size
        return total

    def _execute_many_batch(self, cursor, sql_query: str, batch: Sequence[Any]) -> int:
        if not batch:
            return 0
        try:
            cursor.executemany(sql_query, batch)
            return cursor.rowcount
        except (pymysql.err.OperationalError, pymysql.err.InterfaceError):
            if len(batch) <= 1:
                raise
            # mid = max(len(batch) // 2, 1)
            mid = (len(batch) + 1) // 2
            return self._execute_many_batch(cursor, sql_query, batch[:mid]) + self._execute_many_batch(
                cursor, sql_query, batch[mid:]
            )

    def fetch_query_safe(self, sql_query, params=None, *, timeout_override: float | None = None):
        """Return all rows for a query while converting SQL failures into logs."""
        try:
            return self.fetch_query(sql_query, params, timeout_override=timeout_override)
        except pymysql.MySQLError as e:
            logger.error("event=db_fetch_failed sql=%s error=%s", sql_query, e)
            logger.debug(f"fetch_query - SQL error: {e}<br>{sql_query}, params:")
            logger.debug(params)
            return []

    def execute_query_safe(self, sql_query, params=None, *, timeout_override: float | None = None):
        """Execute a statement while swallowing PyMySQL exceptions."""
        try:
            return self.execute_query(sql_query, params, timeout_override=timeout_override)
        except pymysql.MySQLError as e:
            logger.error("event=db_execute_failed sql=%s error=%s", sql_query, e)
            logger.debug(f"execute_query - SQL error: {e}<br>{sql_query}, params:")
            logger.debug(params)
            if sql_query.strip().lower().startswith("select"):
                return []
            return 0
