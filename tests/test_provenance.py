"""Tests for structured source provenance and snapshot integrity."""

from pathlib import Path

import pytest

from src.provenance import SourceMetadataError, validate_raw_snapshot


def test_current_raw_snapshot_matches_recorded_fingerprint() -> None:
    metadata = validate_raw_snapshot()

    assert metadata["provider"] == "Statistics Norway"
    assert metadata["table_id"] == "14091"
    assert metadata["snapshot"]["retrieved_on"].endswith("Z")
    assert metadata["snapshot"]["period_end"] == "2026M07"
    assert metadata["snapshot"]["record_count"] == 1216


def test_validate_raw_snapshot_rejects_changed_file(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    metadata_path = tmp_path / "source.json"
    raw_path.write_text("changed", encoding="utf-8")
    metadata_path.write_text(
        """{
          "provider": "Provider",
          "table_id": "1",
          "title": "Title",
          "table_url": "https://example.com/table",
          "api_url": "https://example.com/api",
          "unit": "MWh",
          "frequency": "monthly",
          "license": {
            "identifier": "Example",
            "name": "Example license",
            "url": "https://example.com/license"
          },
          "snapshot": {
            "file": "raw.csv",
            "retrieved_on": null,
            "period_start": "2025M01",
            "period_end": "2025M01",
            "verified_on": "2026-09-03",
            "raw_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
          }
        }""",
        encoding="utf-8",
    )

    with pytest.raises(SourceMetadataError, match="não corresponde"):
        validate_raw_snapshot(raw_path, metadata_path)
