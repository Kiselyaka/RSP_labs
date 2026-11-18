from datetime import datetime, timezone
from http import HTTPStatus
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from internal.controller.dto import Error, ErrorBody, FieldIssue
from internal.domain.errors import (
    ErrAlreadyExists, ErrConflict, ErrInvalidInput, ErrNotFound, ErrServiceUnavailable,
    RepositoryError,
)

logger = logging.getLogger(__name__)
ERRORS = {
    ErrInvalidInput: (400, "INVALID_INPUT"),
    ErrNotFound: (404, "NOT_FOUND"),
    ErrAlreadyExists: (409, "CONFLICT"),
    ErrConflict: (409, "CONFLICT"),
    ErrServiceUnavailable: (503, "SERVICE_UNAVAILABLE"),
}
MALFORMED_TYPES = {
    "json_invalid", "extra_forbidden", "model_attributes_type", "model_type",
    "string_type", "int_type", "bool_type", "list_type", "dict_type", "uuid_type",
}


def field_name(location: tuple) -> str:
    parts = list(location)
    source = parts.pop(0) if parts and parts[0] in ("body", "path", "query", "header") else "body"
    if not parts or source == "body" and isinstance(parts[0], int):
        return source
    result = ""
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else ("." if result else "") + str(part)
    return result


def issue_message(error: dict) -> str:
    kind, context = error["type"], error.get("ctx", {})
    messages = {
        "missing": "Field is required.", "extra_forbidden": "Unknown field.",
        "string_pattern_mismatch": "Invalid format.", "string_type": "Must be a string.",
        "int_type": "Must be an integer.", "int_parsing": "Must be an integer.",
        "bool_type": "Must be a boolean.", "bool_parsing": "Must be a boolean.",
        "uuid_parsing": "Must be a valid UUID.", "uuid_type": "Must be a valid UUID.",
        "literal_error": "Value is not allowed.", "json_invalid": "Malformed JSON.",
        "list_type": "Must be an array.", "model_attributes_type": "Must be a JSON object.",
        "model_type": "Must be a JSON object.",
        "text_options": "Text questions cannot contain answer options.",
    }
    if kind in messages:
        return messages[kind]
    if kind in ("string_too_short", "too_short"):
        return f"Minimum length is {context.get('min_length')}."
    if kind in ("string_too_long", "too_long"):
        return f"Maximum length is {context.get('max_length')}."
    if kind == "greater_than_equal":
        return f"Must be greater than or equal to {context.get('ge')}."
    if kind == "less_than_equal":
        return f"Must be less than or equal to {context.get('le')}."
    return "Invalid value."


def error_response(request: Request, status: int, code: str, message: str,
                   details: list[FieldIssue] | None = None) -> JSONResponse:
    body = Error(error=ErrorBody(
        code=code, message=message, details=details or [],
        request_id=request.state.request_id, timestamp=datetime.now(timezone.utc),
    ))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json", by_alias=True))


async def unexpected_error(request: Request, exc: Exception):
    logger.error("Unhandled request error", exc_info=(type(exc), exc, exc.__traceback__),
                 extra={"requestId": request.state.request_id})
    return error_response(request, 500, "INTERNAL_ERROR", "An internal error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RepositoryError)
    async def domain_error(request: Request, exc: RepositoryError):
        for error_type, (status, code) in ERRORS.items():
            if isinstance(exc, error_type):
                return error_response(request, status, code, str(exc))
        return await unexpected_error(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        malformed = any(error["loc"] and error["loc"][0] == "body"
                        and error["type"] in MALFORMED_TYPES for error in errors)
        code = "MALFORMED_JSON" if malformed else "VALIDATION_ERROR"
        details = [FieldIssue(field=field_name(error["loc"]), issue=issue_message(error))
                   for error in errors]
        return error_response(request, 400, code, "Request body is invalid." if malformed
                              else "Request validation failed.", details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if exc.status_code >= 500:
            return await unexpected_error(request, exc)
        code = "NOT_FOUND" if exc.status_code == 404 else HTTPStatus(exc.status_code).name
        response = error_response(request, exc.status_code, code, HTTPStatus(exc.status_code).phrase)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    app.add_exception_handler(Exception, unexpected_error)
