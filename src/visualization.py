"""Matplotlib and Seaborn visualizations for the NGDP CLI."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_production_history(
    df: pd.DataFrame,
    *,
    title: str,
) -> None:
    """Create a production history chart for an energy DataFrame."""

    plt.figure(figsize=(12, 6))
    sns.lineplot(
        data=df,
        x="date",
        y="production_mwh",
        hue="energy_source",
    )
    plt.title(title)
    plt.xlabel("Data")
    plt.ylabel("Produção (MWh)")
    plt.tight_layout()


def show_production_charts(df: pd.DataFrame) -> None:
    """Display the complete and recent production histories."""

    sns.set_theme(style="whitegrid")
    first_year = df["date"].min().year
    last_year = df["date"].max().year

    plot_production_history(
        df,
        title=(f"Produção de energia na Noruega ({first_year}–{last_year})"),
    )

    recent_df = df[df["date"].dt.year >= 2015]
    plot_production_history(
        recent_df,
        title="Produção recente de energia na Noruega (2015+)",
    )

    plt.show()
