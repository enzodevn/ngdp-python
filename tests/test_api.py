"""HTTP contract tests for the NGDP V3 API foundation."""

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.api.app import app
from src.api.auth import API_TOKEN_ENV_VAR

client = TestClient(app)
TEST_API_TOKEN = "ngdp-test-token-with-at-least-32-characters"


def test_health_endpoint_exposes_versioned_service_contract() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ngdp-api",
        "api_version": "v1",
    }


def test_health_endpoint_remains_public_when_authentication_is_unset(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv(API_TOKEN_ENV_VAR, raising=False)

    response = client.get("/health")

    assert response.status_code == 200


def test_energy_summary_fails_closed_when_authentication_is_unset(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv(API_TOKEN_ENV_VAR, raising=False)

    response = client.get("/api/v1/energy/summary")

    assert response.status_code == 503
    assert response.json() == {"detail": "API authentication is not configured."}


def test_energy_summary_rejects_missing_bearer_token(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv(API_TOKEN_ENV_VAR, TEST_API_TOKEN)

    response = client.get("/api/v1/energy/summary")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_energy_summary_rejects_invalid_bearer_token(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv(API_TOKEN_ENV_VAR, TEST_API_TOKEN)

    response = client.get(
        "/api/v1/energy/summary",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_authenticated_energy_summary_uses_the_validated_csv_snapshot(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv(API_TOKEN_ENV_VAR, TEST_API_TOKEN)

    response = client.get(
        "/api/v1/energy/summary",
        headers={"Authorization": f"Bearer {TEST_API_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "backend": "csv",
        "record_count": 1216,
        "source_count": 4,
        "month_count": 403,
        "period_start": "1993-01",
        "period_end": "2026-07",
        "total_mwh": 4519175624.0,
        "latest_month_mwh": 10388060.0,
    }


def test_openapi_schema_documents_the_versioned_summary() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/energy/summary" in schema["paths"]
    security_schemes = schema["components"]["securitySchemes"]
    assert any(
        definition.get("type") == "http" and definition.get("scheme") == "bearer"
        for definition in security_schemes.values()
    )
    assert schema["paths"]["/api/v1/energy/summary"]["get"]["security"]
