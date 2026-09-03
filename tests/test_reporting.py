"""Tests for report formatting and persistence."""

from pathlib import Path

from src.reporting import generate_report, save_report


def test_generate_report_uses_canonical_name() -> None:
    report = generate_report(
        {
            "total": 600.0,
            "media": 200.0,
            "maximo": 300.0,
            "minimo": 100.0,
        }
    )

    assert report.startswith("===== NGDP REPORT =====")
    assert "Produção Média por Registro: 200.00 MWh" in report


def test_save_report_creates_parent_directory(tmp_path: Path) -> None:
    output_path = tmp_path / "outputs" / "report.txt"

    saved_path = save_report("NGDP", output_path)

    assert saved_path == output_path
    assert output_path.read_text(encoding="utf-8") == "NGDP"
