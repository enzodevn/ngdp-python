# NEXUS integration contract

## Current position

NGDP is presented inside NEXUS as a portfolio case study, while its Python
pipeline, dashboard and API run as an independent system. V3 prepares a safe
integration contract; it does not yet connect the public browser directly to
the private API.

## Safe target flow

```text
NEXUS interface
      |
      v
trusted NEXUS backend or integration proxy
      |
      | Authorization: Bearer <server-side token>
      v
NGDP /api/v1/energy/summary
      |
      v
validated NGDP analytical gateway
```

The NGDP bearer token must remain server-side. Embedding it in NEXUS JavaScript,
HTML, a public repository or browser storage would expose the credential and is
not an acceptable integration design.

## Available contracts

| NGDP route | Access | Intended NEXUS use |
| --- | --- | --- |
| `GET /health/live` | Public | Process state and API identity |
| `GET /health/ready` | Public | Active-backend operational state |
| `GET /health` | Public | Compatible process-health contract |
| `GET /api/v1/energy/summary` | Bearer token | Validated headline indicators |
| `GET /openapi.json` | Public | Machine-readable interface contract |

The summary response can supply record count, source count, month count, period
coverage, total production and the latest monthly production value. NEXUS must
label these as real dataset indicators rather than decorative telemetry.

## Integration gate

Before NEXUS consumes live NGDP data, the following must be available:

1. A deployed NGDP API reachable from a trusted integration layer.
2. Server-side secret storage and token rotation.
3. Explicit cross-origin and network access rules.
4. Timeouts, error handling and a truthful unavailable state in NEXUS.
5. Monitoring for the API and its selected data backend.

Until that gate is complete, NEXUS should continue using reviewed static project
metadata and link to the independent NGDP experience.
