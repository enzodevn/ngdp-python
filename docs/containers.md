# Container operations

## Purpose

The NGDP container foundation packages the authenticated analytical API and a
PostgreSQL 17 service into one reproducible local environment. It does not
publish the API or introduce a cloud provider. Public delivery remains a later,
reviewed infrastructure decision.

## Runtime map

```text
local browser or API client
             |
             v
  127.0.0.1:8000 only
             |
             v
     non-root API container
       |              |
       | CSV default  | optional PostgreSQL reads
       v              v
versioned snapshot  internal container network
                            |
                            v
                  PostgreSQL 17 container
                            |
                            v
                    named Docker volume
```

The API port is bound to the loopback interface. PostgreSQL is not published to
the host. Both services have health checks, and the API waits for PostgreSQL to
be ready before starting.

## Prerequisites

- Docker Desktop with Docker Compose v2.
- A local `.env` file created from `.env.example`.
- A random API token containing at least 32 characters.

Create the local configuration in PowerShell:

```powershell
Copy-Item .env.example .env
$token = python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `.env`, replace both placeholder secrets and keep the file local. Git
ignores `.env` files, and the Compose definition does not contain real
credentials.

## Start and verify

Build and start the environment:

```powershell
docker compose up --build --detach
docker compose ps
```

Verify the public operational endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

The OpenAPI interface is available at `http://127.0.0.1:8000/docs`. Protected
analytical routes continue to require the configured bearer token.

## PostgreSQL adoption gate

CSV remains the safe default. To prepare the database with the current trusted
snapshot, run the existing synchronization command inside the API image:

```powershell
docker compose run --rm api python main.py --sync-database --no-charts
```

Set `NGDP_DATA_BACKEND=postgresql` in the local `.env` file and recreate the API
container only after synchronization succeeds:

```powershell
docker compose up --detach --force-recreate api
```

Every PostgreSQL analytical read still passes the exact parity gate against the
canonical CSV snapshot.

## Stop or reset

Stop the services while preserving the database volume:

```powershell
docker compose down
```

Removing the named database volume deletes the local containerized database and
must be an explicit decision. It is not part of the normal shutdown procedure.

## Security boundaries

- The API process runs as the dedicated unprivileged user `ngdp`.
- Linux capabilities are dropped and privilege escalation is disabled.
- The API filesystem is read-only except for isolated temporary and report
  directories.
- Credentials are injected at runtime and are not baked into the image.
- The database is reachable only through the internal Compose network.
- The container image includes only API runtime dependencies and required data.

## Continuous validation

The quality workflow builds the API image and starts it with an ephemeral token.
The workflow accepts the image only when the public health contract responds
successfully. PostgreSQL integration continues to run in its dedicated job.
