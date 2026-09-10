"""Structured logging configuration tests."""

import json
import logging

import pytest

from src.api.observability import (
    JsonLogFormatter,
    resolve_log_level,
    resolve_request_log_level,
)


def test_json_log_formatter_emits_the_operational_request_contract() -> None:
    record = logging.LogRecord(
        name="ngdp.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "d" * 32
    record.method = "GET"
    record.path = "/health/ready"
    record.status_code = 200
    record.duration_ms = 1.25

    event = json.loads(JsonLogFormatter().format(record))

    assert event["level"] == "info"
    assert event["logger"] == "ngdp.api"
    assert event["event"] == "http_request_completed"
    assert event["request_id"] == "d" * 32
    assert event["method"] == "GET"
    assert event["path"] == "/health/ready"
    assert event["status_code"] == 200
    assert event["duration_ms"] == 1.25
    assert "authorization" not in event


def test_log_level_uses_a_safe_default_and_accepts_supported_values() -> None:
    assert resolve_log_level(environ={}) == logging.INFO
    assert resolve_log_level("warning") == logging.WARNING


def test_log_level_rejects_an_unsupported_value() -> None:
    with pytest.raises(ValueError, match="NGDP_LOG_LEVEL"):
        resolve_log_level("verbose")


def test_request_log_level_reduces_probe_noise_and_surfaces_failures() -> None:
    assert (
        resolve_request_log_level(path="/health/ready", status_code=200)
        == logging.DEBUG
    )
    assert (
        resolve_request_log_level(path="/api/v1/energy/summary", status_code=200)
        == logging.INFO
    )
    assert (
        resolve_request_log_level(path="/health/ready", status_code=503)
        == logging.WARNING
    )
