from contextlib import contextmanager

from k3_rms.config import DatabaseSettings
from k3_rms.exceptions import ApplicationError

try:
    import mysql.connector
    from mysql.connector import Error
    from mysql.connector.pooling import MySQLConnectionPool
except ImportError:  # pragma: no cover - import error depends on environment
    mysql = None
    Error = Exception
    MySQLConnectionPool = None


class DatabaseManager:
    """Creates and serves MySQL connections through a small pool."""

    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings
        self._pool = None
        if mysql is None or MySQLConnectionPool is None:
            raise ApplicationError(
                "mysql-connector-python is missing. Install dependencies with 'pip install -r requirements.txt'."
            )

    def ensure_database_exists(self) -> None:
        try:
            connection = mysql.connector.connect(
                host=self.settings.host,
                port=self.settings.port,
                user=self.settings.user,
                password=self.settings.password,
            )
        except Error as exc:
            raise ApplicationError(f"Unable to reach MySQL server: {exc}") from exc
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.settings.database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            connection.commit()
            cursor.close()
        finally:
            connection.close()

    def connect(self) -> None:
        if self._pool is None:
            self.ensure_database_exists()
            try:
                self._pool = MySQLConnectionPool(
                    pool_name="k3_rms_pool",
                    pool_size=5,
                    host=self.settings.host,
                    port=self.settings.port,
                    user=self.settings.user,
                    password=self.settings.password,
                    database=self.settings.database,
                    autocommit=False,
                    connection_timeout=10,
                )
            except Error as exc:
                raise ApplicationError(f"Unable to open the MySQL connection pool: {exc}") from exc

    @contextmanager
    def session(self):
        if self._pool is None:
            self.connect()
        connection = self._pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            yield connection, cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def ping(self) -> None:
        try:
            with self.session():
                return
        except Error as exc:
            raise RuntimeError(f"Unable to connect to MySQL: {exc}") from exc
