import pandas as pd

RAW_FILE = "data_raw/norway_energy_raw.csv"
OUTPUT_FILE = "data_processed/norway_energy_cleaned.csv"

def clean_energy_data():

    df = pd.read_csv(RAW_FILE, sep=";", skiprows=1)

    df = df.rename(columns={"production and consumption": "energy_source"})

    df = df.melt(
        id_vars=["energy_source"],
        var_name="date",
        value_name="production_mwh"
    )

    df = df[df["production_mwh"] != ".."]

    df["production_mwh"] = pd.to_numeric(df["production_mwh"])

    df["date"] = df["date"].str.replace("Electricity power ", "")

    df.to_csv(OUTPUT_FILE, index=False)

    print("Dataset limpo salvo com sucesso!")
    print(df.head())


if __name__ == "__main__":
    clean_energy_data()