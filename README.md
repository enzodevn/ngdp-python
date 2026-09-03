# NGDP — Nordic Green Data Platform

Energy data platform focused on Norwegian electricity production, data
engineering and sustainability.

The NGDP is a NEXUS system and is being developed incrementally. The current
stage consolidates the Python data core before introducing a dedicated web
application, API or database.

## Current status

### Implemented

- Raw monthly electricity dataset for Norway.
- Structured source provenance and snapshot integrity verification.
- On-demand ingestion from the official Statistics Norway PxWebApi v2.
- Read-only update checks and auditable source comparisons.
- Daily source verification that proposes validated changes through a review
  pull request.
- Raw-to-processed transformation with Pandas.
- Validated long-format dataset.
- Monthly production indicators with explicit aggregation semantics.
- Text report generation.
- Matplotlib and Seaborn charts.
- Data-backed Streamlit dashboard prototype.
- Automated tests for cleaning, loading, analytics and reporting.
- Reproducible Python environment through the versioned requirements contract.

### In development

- Deployment workflow that publishes a validated snapshot with the web app.

### Planned

- NGDP Web V1.
- Structured backend API when the interface requires it.
- Database persistence when CSV no longer meets the use case.
- Logging and operational observability.

### Research

- Energy forecasting.
- Anomaly detection.
- Optimization and climate correlation.
- Quantum optimization experiments only as a future NGDP Labs initiative.

## Architecture

    data_raw/norway_energy_raw.csv
    data_raw/source.json
                    |
                    v
          src/ingestion.py <----- Statistics Norway API
                    |
                    v
          provenance verification
                    |
                    v
            src/data_cleaning.py
                    |
                    v
    data_processed/norway_energy_cleaned.csv
                    |
          +---------+---------+
          |                   |
          v                   v
       main.py        src/dashboard.py
          |                   |
          v                   v
    analytics/report     Streamlit UI

Important modules:

- src/config.py: canonical project paths.
- src/data_cleaning.py: transformation of the raw wide table.
- src/data_loading.py: processed-data validation and runtime normalization.
- src/provenance.py: source metadata and raw snapshot integrity verification.
- src/ingestion.py: official API download, schema validation, comparison and
  recoverable snapshot update.
- src/analytics.py: analytical calculations.
- src/reporting.py: text report formatting and persistence.
- src/visualization.py: CLI charts.
- src/main.py: pipeline orchestration and command-line arguments.
- src/dashboard.py: current Streamlit interface.

## Dataset

The raw file identifies itself as Statistics Norway table 14091:
Electricity balance (MWh), by production and consumption, contents and month.

- Official table: https://www.ssb.no/en/statbank/table/14091
- Official API metadata:
  https://data.ssb.no/api/pxwebapi/v2/tables/14091?lang=en
- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0).
- Licence terms: https://www.ssb.no/en/diverse/lisens

Current processed dataset:

- Period: January 1993 through July 2026.
- Frequency: monthly.
- Rows: 1,216.
- Columns: energy_source, date and production_mwh.
- Sources: hydro, wind, solar and thermal power generation.

The current snapshot was retrieved from the official API on 3 September 2026.
Its source update timestamp, retrieval timestamp, period, row count, file hash
and comparison with the previous snapshot are recorded in `data_raw/source.json`.

The local file is a selected subset, not the complete electricity balance
table. Source series also begin in different months. Full schema, indicator
definitions, transformations and limitations are documented in
`docs/data-contract.md`; machine-readable provenance is stored in
`data_raw/source.json`.

The CLI and dashboard use the same indicator semantics. Data is consolidated
by month before the monthly average, peak and minimum are calculated. This
avoids presenting a mean across source rows as if it were a monthly total.

## Requirements

- Python 3.11 or newer.
- Windows PowerShell examples are shown below.

Create a clean environment from the project root:

    py -3.11 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

The existing venv directory is legacy and may reference a Python installation
that no longer exists. New environments should use .venv.

## Running the project

Rebuild the processed dataset directly:

    python -m src.data_cleaning

Verify the source fingerprint, rebuild the processed dataset and generate the
report in one end-to-end run:

    python main.py --rebuild-data --no-charts

Check the official source without changing local files:

    python main.py --check-updates --no-charts

Download, compare, validate and apply an official update before regenerating
the analytical report:

    python main.py --update-from-api --no-charts

The update is rejected if the provider, table identity, dimensions, frequency,
unit or selected series change. Unexpected removals also require manual review.
The dashboard continues to read the validated local snapshot, so it remains
available if the external API is temporarily unavailable.

### Automated source refresh

The GitHub Actions workflow in `.github/workflows/refresh-ssb-data.yml` checks
the official source every day at 08:17 in the `Europe/Oslo` time zone. It can
also be started manually from the Actions page.

If the official snapshot is unchanged, the workflow finishes without creating
a commit. When validated additions or revisions are found, it runs the complete
test suite and opens or updates a pull request from
`automation/ssb-data-update`. The workflow never writes directly to `main`, so
every official data update remains subject to human review.

Run analytics and generate the report without opening charts:

    python main.py --no-charts

Run analytics with interactive charts:

    python main.py

Start the Streamlit dashboard:

    python -m streamlit run src/dashboard.py

The generated canonical report is written to outputs/ngdp_report.txt.

## Tests

Run the test suite from the project root:

    python -m pytest

The tests cover:

- raw-to-processed transformation;
- canonical schema and data validation;
- source metadata and snapshot fingerprint verification;
- official API structure and update safety rules;
- additions, revisions and removals between snapshots;
- execution from a different working directory;
- monthly aggregation semantics;
- report generation;
- pipeline integration, including an end-to-end rebuild, without graphical
  windows.

## Legacy files

The following items belong to the original six-row educational dataset and are
preserved during Sprint 01:

- data/energy_data.csv;
- src/processing.py;
- bar chart (Hydropower, Wind, Solar).png;
- line graph (daily production).png;
- total production graph.png.

They are not part of the canonical monthly pipeline. They should only be moved
or removed in a later change after explicit review.

## Engineering principles

- Add complexity only when the system needs it.
- Preserve raw data and make transformations reproducible.
- Use real metrics rather than decorative telemetry.
- Keep analytics, presentation and future ML responsibilities separate.
- Complete, test and document one capability before adding another platform
  layer.
