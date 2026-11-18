import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from internal.controller.dto import ErrorResponse
from internal.domain.errors import (
    ErrAlreadyExists, ErrConflict, ErrInvalidInput, ErrNotFound, RepositoryError,
)

logger = logging.getLogger(__name__)
ERRORS = {
    ErrInvalidInput: (400, "INVALID_INPUT"),
    ErrNotFound: (404, "NOT_FOUND"),
    ErrAlreadyExists: (409, "ALREADY_EXISTS"),
    ErrConflict: (409, "CONFLICT"),
}


def error_response(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, timestamp=datetime.now(timezone.utc))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RepositoryError)
    async def domain_error(request: Request, exc: RepositoryError):
        for error_type, (status, code) in ERRORS.items():
            if isinstance(exc, error_type):
                return error_response(status, code, str(exc))
        logger.error("Storage operation failed", exc_info=exc)
        return error_response(500, "INTERNAL_ERROR", "An internal error occurred.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not include request values, passwords or driver details in the response.
        return error_response(400, "INVALID_INPUT", "Request body, path or query parameters are invalid.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Unhandled request error", exc_info=exc)
        return error_response(500, "INTERNAL_ERROR", "An internal error occurred.")
