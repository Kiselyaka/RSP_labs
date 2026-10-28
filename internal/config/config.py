import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    app_version: str
    app_environment: str
    app_host: str
    http_port: int


def load_config() -> AppConfig:
    _load_env_file(Path.cwd() / ".env")

    http_port = int(os.getenv("HTTP_PORT", "8080"))
    if not 1 <= http_port <= 65535:
        raise ValueError("HTTP_PORT must be an integer from 1 to 65535.")

    return AppConfig(
        app_name=os.getenv("APP_NAME", "Survey Tool API"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        app_environment=os.getenv("APP_ENV", "development"),
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        http_port=http_port,
    )


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip())
