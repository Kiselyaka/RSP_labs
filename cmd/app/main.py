from contextlib import asynccontextmanager
from time import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
import yaml

from internal.config.config import load_config, load_database_config
from internal.controller.health_controller import create_health_router
from internal.database.postgres import Postgres
from internal.service.health_service import HealthService

config = load_config()
database = Postgres()
health_service = HealthService(config=config, started_at=time(), database=database)
openapi_path = Path(__file__).resolve().parents[2] / "openapi.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        database.open(load_database_config())
        yield
    finally:
        database.close()


app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="Базовый REST API платформы Survey Tool.",
    openapi_url=None,
    docs_url=None,
    lifespan=lifespan,
)
app.include_router(create_health_router(health_service))


def load_openapi_schema() -> dict:
    with openapi_path.open(encoding="utf-8") as openapi_file:
        return yaml.safe_load(openapi_file)


app.openapi = load_openapi_schema


@app.get("/openapi.json", include_in_schema=False)
def get_openapi_schema() -> JSONResponse:
    return JSONResponse(load_openapi_schema())


@app.get("/docs", include_in_schema=False)
def get_swagger_docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{config.app_name} - Swagger UI",
    )


if __name__ == "__main__":
    uvicorn.run(app, host=config.app_host, port=config.http_port)
