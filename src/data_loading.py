"""Load and validate the canonical processed energy dataset."""

import math
from pathlib import Path

import pandas as pd

try:
    from .config import PROCESSED_DATA_PATH
except ImportError:  # Supports direct execution from the src directory.
    from config import PROCESSED_DATA_PATH


REQUIRED_COLUMNS = {"energy_source", "date", "production_mwh"}
SOURCE_PREFIX_PATTERN = r"^\d+\.\d+\s+"
MONTH_VALUE_PATTERN = r"^\d{4}M(?:0[1-9]|1[0-2])$"


class EnergyDataError(ValueError):
    """Raised when an energy dataset does not satisfy the NGDP schema."""


def load_energy_data(
    file_path: str | Path = PROCESSED_DATA_PATH,
) -> pd.DataFrame:
    """Load, validate and normalize the processed energy dataset.

    The CSV remains unchanged on disk. Dates and source labels are normalized
    only in the returned DataFrame for analytics and presentation.
    """

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset processado não encontrado: {path}")

    return validate_energy_data_frame(pd.read_csv(path))


def validate_energy_data_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize energy data from any trusted storage adapter."""

    df = data.copy()

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise EnergyDataError(f"Colunas obrigatórias ausentes: {missing}")

    if df.empty:
        raise EnergyDataError("O dataset processado está vazio.")

    if df[list(REQUIRED_COLUMNS)].isna().any().any():
        raise EnergyDataError("O dataset contém valores ausentes.")

    try:
        df["production_mwh"] = pd.to_numeric(
            df["production_mwh"],
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise EnergyDataError(
            "A coluna production_mwh contém valores não numéricos."
        ) from exc

    if (df["production_mwh"] < 0).any():
        raise EnergyDataError("A coluna production_mwh contém valores negativos.")

    if not df["production_mwh"].map(math.isfinite).all():
        raise EnergyDataError("A coluna production_mwh contém valores infinitos.")

    try:
        date_text = df["date"].astype("string").str.strip()
        if date_text.str.fullmatch(MONTH_VALUE_PATTERN).all():
            df["date"] = pd.to_datetime(date_text, format="%YM%m", errors="raise")
        else:
            df["date"] = pd.to_datetime(df["date"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise EnergyDataError(
            "A coluna date deve conter períodos mensais válidos."
        ) from exc

    if not df["date"].dt.day.eq(1).all():
        raise EnergyDataError("A coluna date deve usar o primeiro dia de cada mês.")

    df["energy_source"] = (
        df["energy_source"]
        .astype("string")
        .str.replace(SOURCE_PREFIX_PATTERN, "", regex=True)
        .str.strip()
    )

    if df["energy_source"].eq("").any():
        raise EnergyDataError("A coluna energy_source contém fontes vazias.")

    if df.duplicated(subset=["energy_source", "date"]).any():
        raise EnergyDataError("O dataset contém fontes e períodos duplicados.")

    return df.sort_values(["date", "energy_source"]).reset_index(drop=True)
