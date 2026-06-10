import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

FILE = "data_processed/norway_energy_cleaned.csv"

def main():

    df = pd.read_csv(FILE)

    # converter data
    df["date"] = pd.to_datetime(df["date"], format="%YM%m")

    # limpar nome da fonte (remover "1.1", "1.2", etc)
    df["energy_source"] = df["energy_source"].str.replace(r"^\d+\.\d+\s", "", regex=True)

    sns.set(style="whitegrid")

    # ----------------------------
    # GRÁFICO 1 — HISTÓRICO TOTAL
    # ----------------------------
    plt.figure(figsize=(12, 6))

    sns.lineplot(data=df, x="date", y="production_mwh", hue="energy_source")

    plt.title("Produção de energia na Noruega (1993–2026)")
    plt.xlabel("Ano")
    plt.ylabel("Produção (MWh)")

    plt.tight_layout()
    plt.show()

    # ----------------------------
    # GRÁFICO 2 — ÚLTIMOS ANOS
    # ----------------------------
    df_recent = df[df["date"].dt.year >= 2015]

    plt.figure(figsize=(12, 6))

    sns.lineplot(data=df_recent, x="date", y="production_mwh", hue="energy_source")

    plt.title("Produção recente de energia na Noruega (2015+)")
    plt.xlabel("Ano")
    plt.ylabel("Produção (MWh)")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()