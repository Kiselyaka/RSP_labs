from time import time

from internal.config.config import AppConfig


class HealthService:
    def __init__(self, config: AppConfig, started_at: float) -> None:
        self._config = config
        self._started_at = started_at

    def get_status(self) -> dict[str, str | int]:
        return {
            "status": "pass",
            "app_name": self._config.app_name,
            "version": self._config.app_version,
            "environment": self._config.app_environment,
            "uptime_seconds": int(time() - self._started_at),
        }
