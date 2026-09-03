"""Pure presentation helpers for the NGDP dashboard."""

from collections.abc import Iterable

import pandas as pd

ENERGY_COLORS = {
    "Hydro power generation": "#2de2e6",
    "Wind power generation": "#7bf1a8",
    "Solar power generation": "#f6d365",
    "Thermal power generation": "#9c7cff",
}
RENEWABLE_SOURCES = {
    "Hydro power generation",
    "Wind power generation",
    "Solar power generation",
}
MONTH_LABELS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def format_energy(value: float) -> str:
    """Format MWh using a compact international unit for the UI."""

    absolute_value = abs(value)
    if absolute_value >= 1_000_000:
        return f"{value / 1_000_000:,.2f} TWh"
    if absolute_value >= 1_000:
        return f"{value / 1_000:,.1f} GWh"
    return f"{value:,.0f} MWh"


def format_exact_energy(value: float) -> str:
    """Format a full MWh value for tooltips and the evidence table."""

    return f"{value:,.0f} MWh"


def format_period(value: pd.Timestamp) -> str:
    """Format a monthly timestamp as a concise dashboard label."""

    return f"{MONTH_LABELS[value.month - 1]} {value.year}"


def filter_dashboard_data(
    data: pd.DataFrame,
    sources: Iterable[str],
    year_range: tuple[int, int],
) -> pd.DataFrame:
    """Apply source and year filters without mutating canonical data."""

    selected_sources = set(sources)
    start_year, end_year = year_range
    mask = data["energy_source"].isin(selected_sources) & data["date"].dt.year.between(
        start_year, end_year
    )
    return data.loc[mask].copy().reset_index(drop=True)


def monthly_totals(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate selected sources into one total per month."""

    return (
        data.groupby("date", as_index=False)["production_mwh"]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )


def latest_energy_mix(data: pd.DataFrame) -> pd.DataFrame:
    """Return source shares for the latest complete dashboard period."""

    latest_date = data["date"].max()
    latest = data.loc[
        data["date"].eq(latest_date),
        ["energy_source", "production_mwh"],
    ].copy()
    total = float(latest["production_mwh"].sum())
    latest["share"] = latest["production_mwh"] / total if total else 0.0
    return latest.sort_values("production_mwh", ascending=False).reset_index(drop=True)


def source_totals(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate total production for each selected source."""

    return (
        data.groupby("energy_source", as_index=False)["production_mwh"]
        .sum()
        .sort_values("production_mwh", ascending=False)
        .reset_index(drop=True)
    )


def renewable_share(data: pd.DataFrame) -> float:
    """Calculate the renewable share for the latest available month."""

    mix = latest_energy_mix(data)
    renewable = mix.loc[
        mix["energy_source"].isin(RENEWABLE_SOURCES),
        "production_mwh",
    ].sum()
    total = mix["production_mwh"].sum()
    return float(renewable / total) if total else 0.0


def latest_change(data: pd.DataFrame) -> float | None:
    """Return the latest monthly production change as a decimal ratio."""

    totals = monthly_totals(data)
    if len(totals) < 2:
        return None
    previous = float(totals.iloc[-2]["production_mwh"])
    current = float(totals.iloc[-1]["production_mwh"])
    if previous == 0:
        return None
    return (current - previous) / previous
