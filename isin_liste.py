import pandas as pd
from pathlib import Path

INPUT_FILE = "data/Wertpapiertransaktionen.csv"
OUTPUT_FILE = "output/wertpapiere.csv"

# Vorgänge, die Wertpapierbestände betreffen
RELEVANTE_VORGAENGE = [
    "Kauf",
    "Verkauf",
    "WP-Einlage",
    "WP-Entnahme"
]

# Bekannte Nicht-ETF-Werte
NICHT_ETF = {
    "KYG393871085",  # GlobalFoundries
    "DE0007100000",  # Daimler
}


def main():

    print("Lese CSV...")

    df = pd.read_csv(
        INPUT_FILE,
        sep=";",
        encoding="utf-16"
    )

    df = df[df["Vorgang"].isin(RELEVANTE_VORGAENGE)]

    wertpapiere = (
        df[["ISIN", "Wertpapier"]]
        .drop_duplicates()
        .sort_values("ISIN")
    )

    wertpapiere["aktiv"] = wertpapiere["ISIN"].apply(
        lambda x: 0 if x in NICHT_ETF else 1
    )

    wertpapiere.columns = [
        "isin",
        "wertpapier",
        "aktiv"
    ]

    wertpapiere.to_csv(
        OUTPUT_FILE,
        sep=";",
        index=False
    )

    print()
    print(f"{len(wertpapiere)} Wertpapiere gefunden")
    print(f"Datei geschrieben: {OUTPUT_FILE}")

    print()
    print(wertpapiere)


if __name__ == "__main__":
    main()