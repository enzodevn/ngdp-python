"""Integration tests for the command-line pipeline."""

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
    assert "4449233092.00 MWh" in report
