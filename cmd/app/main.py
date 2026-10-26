from time import time

import uvicorn
from fastapi import FastAPI

from internal.config.config import load_config
from internal.controller.health_controller import create_health_router
from internal.service.health_service import HealthService

config = load_config()
health_service = HealthService(config=config, started_at=time())

app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="Базовый REST API платформы Survey Tool.",
)
app.include_router(create_health_router(health_service))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=config.http_port)
