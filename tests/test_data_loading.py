"""Tests for canonical data loading and validation."""

from pathlib import Path

import pandas as pd
import pytest

from src.data_loading import EnergyDataError, load_energy_data


def test_load_current_dataset() -> None:
    df = load_energy_data()

    assert len(df) == 1192
    assert df["date"].min() == pd.Timestamp("1993-01-01")
    assert df["date"].max() == pd.Timestamp("2026-01-01")
    assert set(df["energy_source"]) == {
        "Hydro power generation",
        "Wind power generation",
        "Solar power generation",
        "Thermal power generation",
    }
    assert not df.duplicated(subset=["energy_source", "date"]).any()


def test_default_path_does_not_depend_on_current_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert len(load_energy_data()) == 1192


def test_load_energy_data_rejects_missing_columns(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.csv"
    pd.DataFrame({"date": ["2025M01"]}).to_csv(invalid_path, index=False)

    with pytest.raises(EnergyDataError, match="Colunas obrigatórias ausentes"):
        load_energy_data(invalid_path)


def test_load_energy_data_rejects_duplicate_periods(tmp_path: Path) -> None:
    invalid_path = tmp_path / "duplicates.csv"
    pd.DataFrame(
        {
            "energy_source": ["1.1 Hydro", "1.1 Hydro"],
            "date": ["2025M01", "2025M01"],
            "production_mwh": [100, 110],
        }
    ).to_csv(invalid_path, index=False)

    with pytest.raises(EnergyDataError, match="duplicados"):
        load_energy_data(invalid_path)
