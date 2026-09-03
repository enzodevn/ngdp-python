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
- Raw-to-processed transformation with Pandas.
- Validated long-format dataset.
- Monthly production indicators with explicit aggregation semantics.
- Text report generation.
- Matplotlib and Seaborn charts.
- Data-backed Streamlit dashboard prototype.
- Automated tests for cleaning, loading, analytics and reporting.
- Reproducible Python environment through the versioned requirements contract.

### In development

- Automated retrieval from the official API.
- Snapshot update and revision comparison workflow.

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

- Period: January 1993 through January 2026.
- Frequency: monthly.
- Rows: 1,192.
- Columns: energy_source, date and production_mwh.
- Sources: hydro, wind, solar and thermal power generation.

The original snapshot download date was not recorded, so the structured source
record represents it as `null` instead of inferring a date. On 3 September 2026,
the official table was verified as updated through July 2026, while the local
snapshot remains fixed at January 2026.

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
