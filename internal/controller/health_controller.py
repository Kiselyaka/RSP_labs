from fastapi import APIRouter, status
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
    def get_health() -> HealthResponse:
        return HealthResponse(**health_service.get_status())

    return router
