import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    name: str
    max_connections: int


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    app_version: str
    app_environment: str
    app_host: str
    http_port: int


def load_database_config() -> DatabaseConfig:
    return DatabaseConfig(
        host=_required_env("DB_HOST"),
        port=_required_int("DB_PORT", maximum=65535),
        user=_required_env("DB_USER"),
        password=_required_env("DB_PASSWORD"),
        name=_required_env("DB_NAME"),
        max_connections=_required_int("DB_MAX_CONNS"),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise ValueError(f"{name} is required. Set it in .env or the process environment.")
    return value


def _required_int(name: str, maximum: int | None = None) -> int:
    value = _required_env(name)
    message = f"{name} must be a positive integer"
    if maximum is not None:
        message += f" no greater than {maximum}"
    try:
        number = int(value)
    except ValueError:
        raise ValueError(message) from None
    if number < 1 or (maximum is not None and number > maximum):
        raise ValueError(message)
    return number


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
