"""Tests for analytical calculations."""

import pandas as pd
import pytest

from src.analytics import calculate_statistics


def test_calculate_statistics() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2025-01-01", "2025-01-01", "2025-02-01", "2025-02-01"]
            ),
            "energy_source": ["Hydro", "Wind", "Hydro", "Wind"],
            "production_mwh": [100, 20, 200, 40],
        }
    )

    assert calculate_statistics(df) == {
        "total_mwh": 360.0,
        "monthly_average_mwh": 180.0,
        "monthly_peak_mwh": 240.0,
        "monthly_minimum_mwh": 120.0,
        "latest_month_mwh": 240.0,
        "period_start": "2025-01",
        "period_end": "2025-02",
        "month_count": 2,
        "source_count": 2,
    }


def test_calculate_statistics_rejects_empty_data() -> None:
    df = pd.DataFrame(columns=["date", "energy_source", "production_mwh"])

    with pytest.raises(ValueError, match="dados vazios"):
        calculate_statistics(df)


def test_calculate_statistics_requires_monthly_dimensions() -> None:
    df = pd.DataFrame({"production_mwh": [100]})

    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        calculate_statistics(df)
