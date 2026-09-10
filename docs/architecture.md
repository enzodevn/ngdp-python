# NGDP system architecture

## Purpose

NGDP V3 is a read-oriented Norwegian energy data platform. It preserves an
official Statistics Norway snapshot, validates every transformation, offers a
controlled CSV or PostgreSQL analytical path, and exposes the resulting
indicators through a dashboard, command-line workflow and authenticated API.

## System map

```text
Statistics Norway PxWebApi v2
              |
              v
      ingestion + schema gate
              |
              v
 raw snapshot + provenance metadata
              |
              v
 cleaning + canonical validation
              |
              v
     processed CSV snapshot
              |
       +------+------+
       |             |
       v             v
   CSV gateway   PostgreSQL sync
       |             |
       +------v------+
              |
      exact parity gate
              |
       +------+------+----------------+
       |             |                |
       v             v                v
      CLI      Streamlit Web V1   FastAPI /api/v1
                                      |
                                      v
                              HTTP bearer boundary
```

## Component responsibilities

- `src/ingestion.py` validates provider identity, table dimensions, units and
  update shape before a source change can be applied.
- `src/provenance.py` binds the raw snapshot to its origin and content hash.
- `src/data_cleaning.py` transforms the provider table into the canonical long
  format.
- `src/data_loading.py` validates the processed analytical contract.
- `src/database.py` owns migrations and transactional PostgreSQL synchronization.
- `src/data_access.py` selects CSV or PostgreSQL and blocks database reads when
  exact source-period-value parity is not proven.
- `src/analytics.py` contains reusable calculations independent of presentation.
- `src/dashboard_presenter.py` prepares tested dashboard views and filters.
- `src/dashboard.py` composes the interactive Streamlit interface.
- `src/api/service.py` adapts trusted analytics to HTTP response contracts.
- `src/api/models.py` defines immutable Pydantic response models.
- `src/api/auth.py` protects analytical routes with an environment-backed token.
- `src/api/app.py` composes the FastAPI application and operational health route.
- `src/api/observability.py` emits safe structured request events and correlation
  identifiers without recording credentials or query strings.
- `Dockerfile` packages the API in a non-root Python runtime.
- `compose.yaml` defines the local API, PostgreSQL and persistent-volume topology.

## Trust boundaries

```text
external provider
      |
      v
schema + provenance validation
      |
      v
trusted versioned snapshot
      |
      v
data validation + database parity
      |
      v
trusted analytical gateway
      |
      v
bearer-authenticated API response
```

Unexpected source structure, missing provenance, invalid processed data,
database drift and absent authentication all fail closed. The application does
not silently substitute another backend or expose the configured token.

## Runtime configuration

| Variable | Responsibility | Default |
| --- | --- | --- |
| `NGDP_DATA_BACKEND` | Select `csv` or `postgresql` reads | `csv` |
| `NGDP_DATABASE_URL` | Connect database synchronization and reads | none |
| `NGDP_API_TOKEN` | Authorize protected analytical requests | none |
| `NGDP_API_PORT` | Select the loopback port published by Compose | `8000` |
| `NGDP_LOG_LEVEL` | Select structured application-log severity | `INFO` |
| `NGDP_POSTGRES_DB` | Name the local Compose database | `ngdp` |
| `NGDP_POSTGRES_USER` | Name the local Compose database user | `ngdp` |
| `NGDP_POSTGRES_PASSWORD` | Authenticate the local Compose database | none |

Configuration values remain in the process environment. Real credentials are
never stored in the repository.

## Version model

- Product version: `3.0.0`, defined once in `src/__init__.py`.
- API contract version: `v1`, retained in `/api/v1` paths and health metadata.
- Database schema version: managed independently through numbered SQL migrations.
- Dataset version: represented by source timestamps and snapshot hashes.

These versions describe different compatibility boundaries and should not be
forced to advance together.

## Operational states

- `200`: the requested public or authenticated contract completed successfully.
- `401`: bearer credentials are absent or invalid.
- `503`: authentication is not configured or the validated analytical snapshot
  is unavailable.

`GET /health/live` proves that the API process can respond. `GET /health/ready`
validates the selected analytical backend and, for PostgreSQL, the existing
exact parity gate. `GET /health` remains as the original compatible
process-health contract. Operational routes are public; analytical data remains
protected.

## Current deployment boundary

The V3 application contracts are validated locally and in GitHub Actions. The
V4 infrastructure layer adds a reproducible container boundary, backend-aware
readiness and structured application logs. Public hosting, managed PostgreSQL,
centralized telemetry, user accounts, roles and write operations remain
intentionally deferred to later releases.
