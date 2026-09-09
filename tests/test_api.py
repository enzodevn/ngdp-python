"""HTTP contract tests for the NGDP V3 API foundation."""

from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health_endpoint_exposes_versioned_service_contract() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ngdp-api",
        "api_version": "v1",
    }


def test_energy_summary_uses_the_validated_csv_snapshot() -> None:
    response = client.get("/api/v1/energy/summary")

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
    assert "/api/v1/energy/summary" in response.json()["paths"]
