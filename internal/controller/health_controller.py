from fastapi import APIRouter, status
from pydantic import BaseModel

from internal.controller.dto import Error
from internal.domain.errors import ErrServiceUnavailable
from internal.service.health_service import HealthService


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    uptime_seconds: int


def create_health_router(health_service: HealthService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["Health"])

    @router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK,
                responses={503: {"model": Error}, 500: {"model": Error}})
    def get_health() -> HealthResponse:
        if not health_service.is_ready():
            raise ErrServiceUnavailable("PostgreSQL is unavailable.")
        return HealthResponse(**health_service.get_status())

    return router
