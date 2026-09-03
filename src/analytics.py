"""Analytical calculations for NGDP energy data."""

from typing import TypedDict

import pandas as pd


class EnergyStatistics(TypedDict):
    """Summary statistics generated from production observations."""

    total: float
    media: float
    maximo: float
    minimo: float


def calculate_statistics(df: pd.DataFrame) -> EnergyStatistics:
    """Calculate production statistics for a non-empty DataFrame."""

    if "production_mwh" not in df.columns:
        raise ValueError("Coluna obrigatória ausente: production_mwh")

    if df.empty:
        raise ValueError("Não é possível calcular estatísticas de dados vazios.")

    production = df["production_mwh"]
    return {
        "total": float(production.sum()),
        "media": float(production.mean()),
        "maximo": float(production.max()),
        "minimo": float(production.min()),
    }
