# NGDP PostgreSQL foundation

Sprint 07 introduces PostgreSQL as a durable analytical layer while preserving
the validated CSV pipeline as the stable source of truth during the V2
transition.

## Boundary

The official Statistics Norway snapshot is still downloaded, verified and
transformed before database synchronization. PostgreSQL never bypasses source
validation and the dashboard does not depend on the database yet.

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

This boundary keeps V1 operational while the database layer is tested and
adopted incrementally.

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

## Next adoption gate

Before the dashboard reads PostgreSQL, the database path must pass its
integration test in CI and produce the same record count, period and aggregate
values as the canonical CSV. Until that gate passes, CSV remains the runtime
fallback.
