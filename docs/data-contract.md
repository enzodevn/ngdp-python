# NGDP data contract

## Official source

The current dataset is a local snapshot of Statistics Norway Statbank table
14091, *Electricity balance (MWh), by production and consumption, contents and
month*. The table uses MWh, a monthly frequency and the entire month as its
reference period.

The source is licensed under Creative Commons Attribution 4.0 International
(CC BY 4.0). NGDP transforms and presents a selected subset of the official
table and does not imply endorsement by Statistics Norway.

Source links:

- Table: https://www.ssb.no/en/statbank/table/14091
- API metadata: https://data.ssb.no/api/pxwebapi/v2/tables/14091?lang=en
- Licence: https://www.ssb.no/en/diverse/lisens

Machine-readable provenance is stored in `data_raw/source.json`. The current
retrieval timestamp, official update timestamp and differences from the prior
snapshot are recorded there. The file fingerprint protects the recorded
snapshot from silent replacement.

## Raw snapshot

`data_raw/norway_energy_raw.csv` is a versioned input snapshot with four
selected generation series:

- hydro power generation;
- wind power generation;
- solar power generation;
- thermal power generation.

Its current period runs from 1993M01 through 2026M07. A cell containing `..`
means the source did not publish a usable value for that series and month;
these cells are excluded during transformation.

The ingestion pipeline requests all four series from the official PxWebApi v2,
validates the table identity and schema, compares source-month observations and
only then replaces the local raw and processed snapshots. Additions and
revisions are recorded. Unexpected removals stop the update for manual review.

The scheduled workflow checks the source every day at 08:17 in the
`Europe/Oslo` time zone. An unchanged source produces no commit. A validated
change is isolated in `automation/ssb-data-update`, tested and proposed through
a pull request; the workflow does not update `main` directly.

## Canonical processed schema

`data_processed/norway_energy_cleaned.csv` contains one source-month observation
per row:

| Column | Runtime type | Contract |
| --- | --- | --- |
| `energy_source` | string | Non-empty source label; numeric hierarchy prefix removed at runtime. |
| `date` | monthly timestamp | Source format `YYYYMmm`, parsed to the first day of the month. |
| `production_mwh` | numeric | Finite, non-negative electricity production in MWh. |

The combination of `energy_source` and `date` must be unique. Missing required
columns, empty data, invalid periods, duplicates, negative values and infinite
values stop the pipeline with a validation error.

## Indicator semantics

For a filtered dataset, NGDP first sums every available selected source by
month. Indicators then mean:

- **Accumulated production:** sum of all monthly source observations.
- **Monthly average:** mean of the consolidated monthly totals.
- **Monthly peak:** highest consolidated monthly total.
- **Monthly minimum:** lowest consolidated monthly total.
- **Latest month:** consolidated total for the latest available month.

When only one source is selected, the consolidated monthly value is that
source's value. This makes CLI and dashboard indicators use the same semantics.

## Known limitations

- The dashboard reads a validated local snapshot rather than querying the API
  on every page load.
- It represents four generation series, not all 26 categories in table 14091.
- Availability differs by technology, so early consolidated months include
  fewer active series than recent months.
- Official historical values can be revised after the snapshot date.
- Scheduled verification depends on the availability of GitHub Actions and the
  official Statistics Norway API; failed runs require operational review.
