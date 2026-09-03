"""Tests for safe Statistics Norway API ingestion."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pytest

from src.data_cleaning import clean_energy_data
from src.data_loading import load_energy_data
from src.ingestion import (
    IngestionError,
    PreparedUpdate,
    UpdateSummary,
    apply_official_update,
    compare_datasets,
    prepare_official_update,
)


SOURCE_LABELS = {
    "1.1": "Hydro power generation",
    "1.2": "Wind power generation",
    "1.3": "Solar power generation",
    "1.4": "Thermal power generation",
}


def _raw_csv(periods: list[str], values: list[list[int]]) -> str:
    header = ["\"production and consumption\""]
    header.extend(f'"Electricity power {period}"' for period in periods)
    lines = ['"Example electricity table"', ";".join(header)]
    for (code, label), row_values in zip(SOURCE_LABELS.items(), values):
        lines.append(
            ";".join([f'"{code} {label}"', *[str(value) for value in row_values]])
        )
    return "\n".join(lines) + "\n"


def _metadata(raw_path: Path) -> dict[str, Any]:
    return {
        "provider": "Statistics Norway",
        "table_id": "14091",
        "title": "Example electricity table",
        "table_url": "https://example.com/table",
        "api_url": "https://example.com/tables/14091",
        "unit": "MWh",
        "frequency": "monthly",
        "license": {
            "identifier": "CC BY 4.0",
            "name": "Creative Commons Attribution 4.0 International",
            "url": "https://example.com/license",
        },
        "snapshot": {
            "file": raw_path.name,
            "retrieved_on": None,
            "period_start": "2025M01",
            "period_end": "2025M01",
            "verified_on": "2025-01-01",
            "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        },
    }


def _table_metadata() -> dict[str, Any]:
    return {
        "id": "14091",
        "source": "Statistics Norway",
        "timeUnit": "Monthly",
        "variableNames": [
            "production and consumption",
            "contents",
            "month",
        ],
        "updated": "2025-03-01T08:00:00Z",
        "lastPeriod": "2025M02",
    }


def _data_payload(unit: str = "MWh") -> dict[str, Any]:
    periods = ["2025M01", "2025M02"]
    return {
        "version": "2.0",
        "class": "dataset",
        "source": "Statistics Norway",
        "id": ["Produk2", "ContentsCode", "Tid"],
        "size": [4, 1, 2],
        "dimension": {
            "Produk2": {
                "category": {
                    "index": {code: index for index, code in enumerate(SOURCE_LABELS)},
                    "label": SOURCE_LABELS,
                }
            },
            "ContentsCode": {
                "category": {
                    "index": {"Kraft": 0},
                    "label": {"Kraft": "Electricity power"},
                    "unit": {"Kraft": {"base": unit, "decimals": 0}},
                }
            },
            "Tid": {
                "category": {
                    "index": {period: index for index, period in enumerate(periods)},
                    "label": {period: period for period in periods},
                }
            },
        },
        "value": [10, 11, 20, 21, 30, 31, 40, 41],
    }


def _prepare_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "processed.csv"
    metadata_path = tmp_path / "source.json"
    raw_path.write_text(
        _raw_csv(["2025M01"], [[10], [20], [30], [40]]),
        encoding="utf-8",
        newline="",
    )
    clean_energy_data(raw_path, processed_path, verbose=False)
    metadata_path.write_text(
        json.dumps(_metadata(raw_path)),
        encoding="utf-8",
    )
    return raw_path, processed_path, metadata_path


def test_prepare_and_apply_official_update(tmp_path: Path) -> None:
    raw_path, processed_path, metadata_path = _prepare_paths(tmp_path)

    def fake_loader(
        url: str,
        params: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        if url.endswith("/data"):
            assert params is not None
            assert params["valueCodes[Produk2]"] == "1.1,1.2,1.3,1.4"
            return _data_payload()
        assert params == {"lang": "en"}
        return _table_metadata()

    prepared = prepare_official_update(
        raw_path=raw_path,
        processed_path=processed_path,
        metadata_path=metadata_path,
        json_loader=fake_loader,
        retrieved_at=datetime(2025, 3, 2, 12, 0, tzinfo=timezone.utc),
    )

    assert prepared.summary == UpdateSummary(
        old_period_end="2025M01",
        new_period_end="2025M02",
        added_rows=4,
        revised_rows=0,
        removed_rows=0,
    )

    apply_official_update(
        prepared,
        raw_path=raw_path,
        processed_path=processed_path,
        metadata_path=metadata_path,
    )

    updated_data = load_energy_data(processed_path)
    updated_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert len(updated_data) == 8
    assert updated_data["date"].max() == pd.Timestamp("2025-02-01")
    assert updated_metadata["snapshot"]["period_end"] == "2025M02"
    assert updated_metadata["snapshot"]["record_count"] == 8
    assert updated_metadata["snapshot"]["retrieved_on"] == "2025-03-02T12:00:00Z"


def test_prepare_official_update_rejects_unit_change(tmp_path: Path) -> None:
    raw_path, processed_path, metadata_path = _prepare_paths(tmp_path)

    def fake_loader(
        url: str,
        params: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        return _data_payload(unit="GWh") if url.endswith("/data") else _table_metadata()

    with pytest.raises(IngestionError, match="unidade oficial"):
        prepare_official_update(
            raw_path=raw_path,
            processed_path=processed_path,
            metadata_path=metadata_path,
            json_loader=fake_loader,
        )


def test_apply_official_update_blocks_removals() -> None:
    update = PreparedUpdate(
        raw_text="",
        processed_text="",
        metadata_text="",
        summary=UpdateSummary(
            old_period_end="2025M02",
            new_period_end="2025M02",
            added_rows=0,
            revised_rows=0,
            removed_rows=1,
        ),
    )

    with pytest.raises(IngestionError, match="revisão manual"):
        apply_official_update(update)


def test_compare_datasets_counts_official_revisions() -> None:
    current = pd.DataFrame(
        {
            "energy_source": ["Hydro"],
            "date": pd.to_datetime(["2025-01-01"]),
            "production_mwh": [10],
        }
    )
    candidate = current.copy()
    candidate["production_mwh"] = [11]

    summary = compare_datasets(current, candidate)

    assert summary.revised_rows == 1
    assert summary.added_rows == 0
    assert summary.removed_rows == 0
