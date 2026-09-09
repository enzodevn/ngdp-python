# NGDP analytical data access

Sprint 08 introduces a controlled gateway between analytical consumers and the
two supported storage backends. The gateway keeps the canonical CSV as the safe
default and allows PostgreSQL only after exact snapshot parity is verified.

## Runtime flow

    analytical consumer
            |
            v
    src/data_access.py
       |          |
       v          v
      CSV     PostgreSQL
       |          |
       +----+-----+
            |
            v
       parity gate
            |
            v
    analytics / dashboard

The PostgreSQL path compares source, period, value and record identity through
the deterministic processed-data SHA-256 fingerprint. It also reports the
record count, source count, coverage period and total production used by the
verification.

## Backend selection

CSV remains the default when no option is supplied:

    python main.py --no-charts

Select PostgreSQL explicitly for one CLI execution:

    python main.py --data-backend postgresql --no-charts

Or configure the process used by the CLI or Streamlit dashboard:

    $env:NGDP_DATA_BACKEND = "postgresql"
    $env:NGDP_DATABASE_URL = "postgresql://ngdp:your-password@localhost:5432/ngdp"
    python -m streamlit run src/dashboard.py

The PostgreSQL database must already contain the validated snapshot. It can be
synchronized and selected in one CLI execution:

    python main.py --sync-database --data-backend postgresql --no-charts

## Failure policy

Selecting PostgreSQL is explicit. If the connection fails, the snapshot is
missing or parity differs, execution stops with a controlled error. The gateway
never silently changes backends because an invisible fallback could hide an
operational or data-integrity problem.

Returning to the stable backend is an explicit configuration change:

    $env:NGDP_DATA_BACKEND = "csv"

## Adoption boundary

This sprint establishes database-backed reads without removing the file-based
pipeline. The CSV remains the canonical recovery path until PostgreSQL-backed
operation has been observed in the target deployment environment.
