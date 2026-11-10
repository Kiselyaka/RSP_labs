from psycopg import Error
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool, PoolTimeout

from internal.config.config import DatabaseConfig


class Postgres:
    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None

    def open(self, config: DatabaseConfig) -> None:
        pool = ConnectionPool(
            conninfo=make_conninfo(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                dbname=config.name,
                connect_timeout=3,
                options="-c statement_timeout=2000",
            ),
            min_size=1,
            max_size=config.max_connections,
            timeout=1,
            max_idle=60,
            max_lifetime=1800,
            reconnect_timeout=25,
            check=ConnectionPool.check_connection,
            open=False,
        )
        self._pool = pool
        try:
            # The pool retries failed connections with backoff during this wait.
            pool.open(wait=True, timeout=20)
        except PoolTimeout as exc:
            raise RuntimeError("PostgreSQL was not reachable within 20 seconds.") from exc

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def is_available(self) -> bool:
        if self._pool is None:
            return False
        try:
            with self._pool.connection() as connection:
                connection.execute("SELECT 1")
        except (Error, PoolTimeout):
            return False
        return True
