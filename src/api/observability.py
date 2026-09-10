"""Structured API logging and request correlation."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

LOG_LEVEL_ENV_VAR = "NGDP_LOG_LEVEL"
API_LOGGER_NAME = "ngdp.api"
REQUEST_ID_HEADER = "X-Request-ID"
SUPPORTED_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
STRUCTURED_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "backend",
    "error_type",
)
QUIET_OPERATIONAL_PATHS = frozenset({"/health", "/health/live", "/health/ready"})


class JsonLogFormatter(logging.Formatter):
    """Render one application event as a compact JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field_name in STRUCTURED_FIELDS:
            if hasattr(record, field_name):
                event[field_name] = getattr(record, field_name)
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False, separators=(",", ":"))


class NgdpJsonStreamHandler(logging.StreamHandler):
    """Identify the handler managed by the NGDP logging configuration."""


def resolve_log_level(
    value: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Resolve a supported level from a value or the process environment."""

    source = os.environ if environ is None else environ
    candidate = value if value is not None else source.get(LOG_LEVEL_ENV_VAR, "")
    level_name = candidate.strip().upper() or "INFO"
    try:
        return SUPPORTED_LOG_LEVELS[level_name]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_LOG_LEVELS)
        raise ValueError(
            f"{LOG_LEVEL_ENV_VAR} must use one of these values: {supported}."
        ) from exc


def configure_api_logging(
    *,
    environ: Mapping[str, str] | None = None,
) -> logging.Logger:
    """Configure one idempotent JSON handler for API application events."""

    logger = logging.getLogger(API_LOGGER_NAME)
    logger.setLevel(resolve_log_level(environ=environ))
    logger.propagate = False

    handler = next(
        (item for item in logger.handlers if isinstance(item, NgdpJsonStreamHandler)),
        None,
    )
    if handler is None:
        handler = NgdpJsonStreamHandler()
        logger.addHandler(handler)
    handler.setFormatter(JsonLogFormatter())
    return logger


def resolve_request_log_level(*, path: str, status_code: int) -> int:
    """Keep successful health probes quiet while surfacing request failures."""

    if status_code >= 500:
        return logging.WARNING
    if path in QUIET_OPERATIONAL_PATHS:
        return logging.DEBUG
    return logging.INFO


class RequestObservabilityMiddleware:
    """Add safe correlation metadata and one structured log per HTTP request."""

    def __init__(self, app: ASGIApp, *, logger: logging.Logger) -> None:
        self.app = app
        self.logger = logger

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        method = str(scope.get("method", "UNKNOWN"))
        path = str(scope.get("path", ""))
        started_at = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            self.logger.exception(
                "http_request_failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                },
            )
            raise

        self.logger.log(
            resolve_request_log_level(path=path, status_code=status_code),
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started_at) * 1000, 3),
            },
        )


LOGGER = configure_api_logging()
