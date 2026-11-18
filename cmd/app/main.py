from contextlib import asynccontextmanager
from time import time

import uvicorn
from fastapi import FastAPI

from internal.config.config import load_config, load_database_config
from internal.controller.health_controller import create_health_router
from internal.controller.errors import register_error_handlers
from internal.controller.resource_controller import router
from internal.controller.request_context import RequestContextMiddleware, configure_logging
from internal.database.postgres import Postgres
from internal.repository.postgres import (
    PostgresQuestionRepository,
    PostgresSurveyRepository,
    PostgresUserRepository,
)
from internal.service.health_service import HealthService
from internal.service.user_service import UserService
from internal.service.survey_service import SurveyService
from internal.repository.survey_session import session_factory

config = load_config()
database = Postgres()
health_service = HealthService(config=config, started_at=time(), database=database)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        database.open(load_database_config())
        app.state.users = PostgresUserRepository(database.connection)
        app.state.surveys = PostgresSurveyRepository(database.connection)
        app.state.questions = PostgresQuestionRepository(database.connection)
        app.state.user_service = UserService(app.state.users)
        app.state.survey_service = SurveyService(session_factory(database))
        yield
    finally:
        database.close()


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="ЛР 8. Валидация DTO, единые ошибки и X-Request-ID. Учебный API без аутентификации.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)
app.include_router(create_health_router(health_service))
app.include_router(router)
register_error_handlers(app)


def openapi_schema() -> dict:
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema is None:
        schema = get_openapi(title=app.title, version=app.version,
                             description=app.description, routes=app.routes)
        # Request validation is intentionally translated to 400 by the common handler.
        for path in schema["paths"].values():
            for operation in path.values():
                if isinstance(operation, dict):
                    operation.get("responses", {}).pop("422", None)
                    for response in operation.get("responses", {}).values():
                        response.setdefault("headers", {})["X-Request-ID"] = {
                            "description": "Server-generated request identifier, also present in error.requestId.",
                            "schema": {"type": "string", "format": "uuid"},
                        }
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = openapi_schema


if __name__ == "__main__":
    configure_logging()
    uvicorn.run(app, host=config.app_host, port=config.http_port, log_config=None, access_log=False)
