from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from internal.service.health_service import HealthService


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    uptime_seconds: int


def create_health_router(health_service: HealthService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["Health"])

    @router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
    def get_health() -> HealthResponse | JSONResponse:
        if not health_service.is_ready():
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "PostgreSQL is unavailable.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        return HealthResponse(**health_service.get_status())

    return router
