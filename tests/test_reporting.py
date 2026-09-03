"""Tests for report formatting and persistence."""

from pathlib import Path

from src.reporting import generate_report, save_report


def test_generate_report_uses_canonical_name() -> None:
    report = generate_report(
        {
            "total_mwh": 600.0,
            "monthly_average_mwh": 200.0,
            "monthly_peak_mwh": 300.0,
            "monthly_minimum_mwh": 100.0,
            "latest_month_mwh": 250.0,
            "period_start": "2025-01",
            "period_end": "2025-03",
            "month_count": 3,
            "source_count": 2,
        }
    )

    assert report.startswith("===== NGDP REPORT =====")
    assert "Período: 2025-01 a 2025-03" in report
    assert "Produção média mensal combinada: 200.00 MWh" in report
    assert "Produção no mês mais recente: 250.00 MWh" in report


def test_save_report_creates_parent_directory(tmp_path: Path) -> None:
    output_path = tmp_path / "outputs" / "report.txt"

    saved_path = save_report("NGDP", output_path)

    assert saved_path == output_path
    assert output_path.read_text(encoding="utf-8") == "NGDP"
