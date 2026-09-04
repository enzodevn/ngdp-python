"""Tests for dashboard-only presentation calculations."""

import pandas as pd
import pytest

from src.dashboard_presenter import (
    filter_dashboard_data,
    format_energy,
    format_period,
    latest_change,
    latest_energy_mix,
    monthly_totals,
    renewable_share,
    source_totals,
)


@pytest.fixture
def dashboard_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "energy_source": [
                "Hydro power generation",
                "Thermal power generation",
                "Hydro power generation",
                "Thermal power generation",
            ],
            "date": pd.to_datetime(
                ["2024-12-01", "2024-12-01", "2025-01-01", "2025-01-01"]
            ),
            "production_mwh": [80.0, 20.0, 90.0, 10.0],
        }
    )


def test_filter_dashboard_data_keeps_sources_and_years(dashboard_data):
    filtered = filter_dashboard_data(
        dashboard_data,
        ["Hydro power generation"],
        (2025, 2025),
    )

    assert filtered["production_mwh"].tolist() == [90.0]


def test_monthly_and_source_aggregations(dashboard_data):
    monthly = monthly_totals(dashboard_data)
    totals = source_totals(dashboard_data)

    assert monthly["production_mwh"].tolist() == [100.0, 100.0]
    assert dict(
        zip(totals["energy_source"], totals["production_mwh"], strict=True)
    ) == {
        "Hydro power generation": 170.0,
        "Thermal power generation": 30.0,
    }


def test_latest_mix_and_renewable_share(dashboard_data):
    mix = latest_energy_mix(dashboard_data)

    assert mix["share"].sum() == pytest.approx(1.0)
    assert renewable_share(dashboard_data) == pytest.approx(0.9)


def test_latest_change_uses_monthly_totals(dashboard_data):
    assert latest_change(dashboard_data) == pytest.approx(0.0)


def test_dashboard_formatters_are_compact():
    assert format_energy(1_250_000) == "1.25 TWh"
    assert format_energy(12_500) == "12.5 GWh"
    assert format_period(pd.Timestamp("2025-01-01")) == "Jan 2025"
