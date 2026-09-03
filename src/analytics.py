"""Analytical calculations for NGDP energy data."""

from typing import TypedDict

import pandas as pd


class EnergyStatistics(TypedDict):
    """Monthly production indicators generated from canonical data."""

    total_mwh: float
    monthly_average_mwh: float
    monthly_peak_mwh: float
    monthly_minimum_mwh: float
    latest_month_mwh: float
    period_start: str
    period_end: str
    month_count: int
    source_count: int


def calculate_statistics(df: pd.DataFrame) -> EnergyStatistics:
    """Calculate period and monthly indicators for a non-empty DataFrame.

    When more than one energy source is present, values are summed by month
    before monthly averages and extrema are calculated. This prevents a row
    average from being presented as a monthly production indicator.
    """

    required_columns = {"date", "energy_source", "production_mwh"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    if df.empty:
        raise ValueError("Não é possível calcular estatísticas de dados vazios.")

    dates = pd.to_datetime(df["date"], errors="raise")
    production = pd.to_numeric(df["production_mwh"], errors="raise")
    monthly_production = (
        pd.DataFrame({"date": dates, "production_mwh": production})
        .groupby("date")["production_mwh"]
        .sum()
        .sort_index()
    )

    return {
        "total_mwh": float(monthly_production.sum()),
        "monthly_average_mwh": float(monthly_production.mean()),
        "monthly_peak_mwh": float(monthly_production.max()),
        "monthly_minimum_mwh": float(monthly_production.min()),
        "latest_month_mwh": float(monthly_production.iloc[-1]),
        "period_start": monthly_production.index.min().strftime("%Y-%m"),
        "period_end": monthly_production.index.max().strftime("%Y-%m"),
        "month_count": len(monthly_production),
        "source_count": int(df["energy_source"].nunique()),
    }
