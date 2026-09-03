"""Integration tests for the command-line pipeline."""

import hashlib
import json
from pathlib import Path

from src.main import run_pipeline


def test_pipeline_generates_report_without_charts(tmp_path: Path) -> None:
    report_path = tmp_path / "ngdp_report.txt"

    saved_path = run_pipeline(
        report_path=report_path,
        show_charts=False,
    )

    report = report_path.read_text(encoding="utf-8")
    assert saved_path == report_path
    assert "===== NGDP REPORT =====" in report
    assert "Produção acumulada: 4449233092.00 MWh" in report
    assert "Meses analisados: 397" in report


def test_pipeline_rebuilds_processed_data_from_verified_snapshot(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "raw.csv"
    metadata_path = tmp_path / "source.json"
    processed_path = tmp_path / "processed.csv"
    report_path = tmp_path / "report.txt"
    raw_path.write_text(
        '"Example table"\n'
        '"production and consumption";'
        '"Electricity power 2025M01";'
        '"Electricity power 2025M02"\n'
        '"1.1 Hydro power generation";100;110\n'
        '"1.2 Wind power generation";20;30\n',
        encoding="utf-8",
    )
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    metadata_path.write_text(
        json.dumps(
            {
                "provider": "Example provider",
                "table_id": "example",
                "title": "Example table",
                "table_url": "https://example.com/table",
                "api_url": "https://example.com/api",
                "unit": "MWh",
                "frequency": "monthly",
                "license": {
                    "identifier": "Example",
                    "name": "Example license",
                    "url": "https://example.com/license",
                },
                "snapshot": {
                    "file": "raw.csv",
                    "retrieved_on": None,
                    "period_start": "2025M01",
                    "period_end": "2025M02",
                    "verified_on": "2026-09-03",
                    "raw_sha256": raw_hash,
                },
            }
        ),
        encoding="utf-8",
    )

    saved_path = run_pipeline(
        raw_data_path=raw_path,
        source_metadata_path=metadata_path,
        data_path=processed_path,
        report_path=report_path,
        rebuild_data=True,
        show_charts=False,
    )

    report = report_path.read_text(encoding="utf-8")
    assert saved_path == report_path
    assert processed_path.is_file()
    assert "Produção média mensal combinada: 130.00 MWh" in report
