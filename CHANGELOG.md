# Changelog

This file records significant NGDP product changes. Product releases use
semantic version tags such as `v3.0.0`; API and database contracts are versioned
independently.

## 3.0.0 - 2026-09-09

### Added

- FastAPI read-only analytical service with OpenAPI documentation.
- Immutable Pydantic contracts for health and energy summary responses.
- Environment-backed HTTP bearer authentication for analytical access.
- Public operational health route with product and API contract versions.
- Architecture and safe NEXUS integration documentation.

### Security

- Analytical requests fail closed when authentication is not configured.
- Missing or invalid credentials return `401` without exposing token values.
- Credentials remain outside versioned files and are compared in constant time.

### Quality

- HTTP behavior and OpenAPI security metadata are covered by automated tests.
- Python 3.11, Python 3.12, PostgreSQL and workflow checks run in CI.
- Source fingerprint validation remains part of the release gate.
