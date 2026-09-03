"""Transform the raw Statistics Norway table into the NGDP long format."""

from pathlib import Path

import pandas as pd

try:
    from .config import PROCESSED_DATA_PATH, RAW_DATA_PATH
except ImportError:  # Supports direct execution from the src directory.
    from config import PROCESSED_DATA_PATH, RAW_DATA_PATH


def clean_energy_data(
    raw_file: str | Path = RAW_DATA_PATH,
    output_file: str | Path = PROCESSED_DATA_PATH,
    *,
    verbose: bool = True,
) -> pd.DataFrame:
    """Clean the wide raw CSV and persist the canonical processed dataset."""

    raw_path = Path(raw_file)
    output_path = Path(output_file)

    if not raw_path.is_file():
        raise FileNotFoundError(f"Dataset bruto não encontrado: {raw_path}")

    df = pd.read_csv(raw_path, sep=";", skiprows=1)

    source_column = "production and consumption"
    if source_column not in df.columns:
        raise ValueError(f"Coluna obrigatória ausente: {source_column}")

    df = df.rename(columns={source_column: "energy_source"})

    df = df.melt(
        id_vars=["energy_source"],
        var_name="date",
        value_name="production_mwh",
    )

    df = df[df["production_mwh"] != ".."].copy()

    df["production_mwh"] = pd.to_numeric(
        df["production_mwh"],
        errors="raise",
    )

    df["date"] = df["date"].str.replace(
        "Electricity power ",
        "",
        regex=False,
    )

    invalid_dates = ~df["date"].str.fullmatch(r"\d{4}M(0[1-9]|1[0-2])")
    if invalid_dates.any():
        raise ValueError("O dataset bruto contém períodos mensais inválidos.")

    if df.duplicated(subset=["energy_source", "date"]).any():
        raise ValueError("A limpeza produziu fontes e períodos duplicados.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    if verbose:
        print(f"Dataset limpo salvo em: {output_path}")
        print(f"Registros processados: {len(df)}")
    return df


if __name__ == "__main__":
    clean_energy_data()
