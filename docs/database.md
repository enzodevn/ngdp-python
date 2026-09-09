# NGDP PostgreSQL foundation

Sprint 07 introduced PostgreSQL as a durable analytical layer. Sprint 08 added
a controlled read gateway while preserving the validated CSV pipeline as the
stable default for the completed V2 scope.

## Boundary

The official Statistics Norway snapshot is still downloaded, verified and
transformed before database synchronization. PostgreSQL never bypasses source
validation. The CLI and dashboard can select it explicitly, but only through
the parity gate documented in `docs/data-access.md`.

    Statistics Norway API
              |
              v
       verified raw snapshot
              |
              v
       canonical processed CSV
              |
              v
       PostgreSQL synchronization
              |
              v
       exact parity gate
              |
              v
       analytical consumers

This boundary keeps the analytical runtime recoverable while the database
layer can be adopted incrementally.

## Relational model

- `ngdp.dataset_source`: stable official table identity and licence metadata.
- `ngdp.source_snapshot`: immutable content versions, coverage and provenance.
- `ngdp.energy_source`: provider codes and normalized generation labels.
- `ngdp.generation_observation`: monthly production facts for each snapshot.
- `ngdp.current_generation`: latest validated snapshot for every dataset.
- `ngdp.schema_migration`: applied migration names and checksums.

Every observation retains its snapshot lineage. Raw and normalized content
receive separate semantic checksums, so either a source revision or an approved
transformation revision creates a new snapshot instead of overwriting history.

## Migration contract

SQL migrations live in `database/migrations` and use the pattern
`NNN_description.sql`. Applied files are recorded with their SHA-256 checksum.
An applied migration must never be edited; a schema change receives the next
versioned file.

## Configuration

Copy `.env.example` only as a reference. The application reads the connection
URL from the process environment and never stores credentials in the
repository.

PowerShell example:

    $env:NGDP_DATABASE_URL = "postgresql://ngdp:your-password@localhost:5432/ngdp"
    python main.py --sync-database --no-charts

Remove the value from the current terminal when it is no longer needed:

    Remove-Item Env:NGDP_DATABASE_URL

The synchronization is transactional and idempotent. Running the same
validated snapshot again keeps one snapshot record and rebuilds its fact rows
inside a single transaction.

## Adoption gate

Before PostgreSQL data reaches analytics or the dashboard, it must pass its
integration test and produce the same deterministic source-period-value
fingerprint as the canonical CSV. The gate also reports record count, source
count, coverage period and total production. CSV remains the default runtime
backend; managed PostgreSQL deployment belongs to a future infrastructure
stage.
