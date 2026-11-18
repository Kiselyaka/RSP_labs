from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import logging.config
from uuid import uuid4

from starlette.requests import Request

request_id: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger(__name__)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "requestId"):
            record.requestId = request_id.get()
        return True


class RequestLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        body = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "requestId": getattr(record, "requestId", request_id.get()),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            body["exception"] = self.formatException(record.exc_info)
        return json.dumps(body, ensure_ascii=False)


def configure_logging() -> None:
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"request_id": {"()": RequestIdFilter}},
        "formatters": {"default": {"()": RequestLogFormatter}},
        "handlers": {"console": {
            "class": "logging.StreamHandler", "formatter": "default", "filters": ["request_id"],
        }},
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {"uvicorn": {"handlers": [], "propagate": True},
                    "uvicorn.error": {"handlers": [], "propagate": True},
                    "uvicorn.access": {"handlers": [], "propagate": True}},
    })


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        identifier = str(uuid4())
        scope.setdefault("state", {})["request_id"] = identifier
        token = request_id.set(identifier)
        response_started = False
        status = 500

        async def send_with_id(message):
            nonlocal response_started, status
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                headers = [(key, value) for key, value in message.get("headers", [])
                           if key.lower() != b"x-request-id"]
                headers.append((b"x-request-id", identifier.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            try:
                await self.app(scope, receive, send_with_id)
            except Exception as exc:
                if response_started:
                    raise
                from internal.controller.errors import unexpected_error
                response = await unexpected_error(Request(scope), exc)
                await response(scope, receive, send_with_id)
        finally:
            logger.info("request method=%s path=%s status=%s", scope["method"], scope["path"],
                        status, extra={"requestId": identifier})
            request_id.reset(token)
