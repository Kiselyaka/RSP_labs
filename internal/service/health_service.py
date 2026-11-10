from time import time

from internal.config.config import AppConfig
from internal.database.postgres import Postgres


class HealthService:
    def __init__(self, config: AppConfig, started_at: float, database: Postgres) -> None:
        self._config = config
        self._started_at = started_at
        self._database = database

    def is_ready(self) -> bool:
        return self._database.is_available()

    def get_status(self) -> dict[str, str | int]:
        return {
            "status": "pass",
            "app_name": self._config.app_name,
            "version": self._config.app_version,
            "environment": self._config.app_environment,
            "uptime_seconds": int(time() - self._started_at),
        }
