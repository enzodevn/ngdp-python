"""Tests for the raw-to-processed transformation."""

from pathlib import Path

from src.data_cleaning import clean_energy_data


def test_clean_energy_data_transforms_wide_input(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    processed_path = tmp_path / "nested" / "processed.csv"
    raw_path.write_text(
        '"Example table"\n'
        '"production and consumption";'
        '"Electricity power 2025M01";'
        '"Electricity power 2025M02"\n'
        '"1.1 Hydro power generation";100;110\n'
        '"1.2 Wind power generation";..;20\n',
        encoding="utf-8",
    )

    result = clean_energy_data(raw_path, processed_path)

    assert processed_path.is_file()
    assert len(result) == 3
    assert list(result.columns) == [
        "energy_source",
        "date",
        "production_mwh",
    ]
    assert set(result["date"]) == {"2025M01", "2025M02"}
    assert set(result["production_mwh"]) == {20, 100, 110}
