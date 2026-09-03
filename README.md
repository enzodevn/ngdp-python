# NGDP — Nordic Green Data Platform

Energy data platform focused on Norwegian electricity production, data
engineering and sustainability.

The NGDP is a NEXUS system and is being developed incrementally. The current
stage consolidates the Python data core before introducing a dedicated web
application, API or database.

## Current status

### Implemented

- Raw monthly electricity dataset for Norway.
- Raw-to-processed transformation with Pandas.
- Validated long-format dataset.
- Production summary statistics.
- Text report generation.
- Matplotlib and Seaborn charts.
- Data-backed Streamlit dashboard prototype.
- Automated tests for cleaning, loading, analytics and reporting.
- Reproducible Python environment through the versioned requirements contract.

### In development

- Consolidation of the command-line and dashboard workflows.
- Data provenance and freshness documentation.

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
- src/analytics.py: analytical calculations.
- src/reporting.py: text report formatting and persistence.
- src/visualization.py: CLI charts.
- src/main.py: pipeline orchestration and command-line arguments.
- src/dashboard.py: current Streamlit interface.

## Dataset

The raw file identifies itself as Statistics Norway table 14091:
Electricity balance (MWh), by production and consumption, contents and month.

Current processed dataset:

- Period: January 1993 through January 2026.
- Frequency: monthly.
- Rows: 1,192.
- Columns: energy_source, date and production_mwh.
- Sources: hydro, wind, solar and thermal power generation.

The repository still needs the original download URL, retrieval date, license
and known dataset limitations documented before automated ingestion is added.

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

Regenerate the processed dataset:

    python -m src.data_cleaning

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
- execution from a different working directory;
- analytical statistics;
- report generation;
- pipeline integration without graphical windows.

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
