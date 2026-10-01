import pandas as pd
from pathlib import Path
from collections import defaultdict

CSV_DATEI = "data/Wertpapiertransaktionen.csv"
OUTPUT_DATEI = "output/monatliche_bestaende.csv"


def lese_csv(datei):
    encodings = [
        "utf-8",
        "utf-16",
        "utf-16-le",
        "cp1252",
        "latin1"
    ]

    for enc in encodings:
        try:
            print(f"Lese Datei mit {enc}")

            df = pd.read_csv(
                datei,
                sep=";",
                decimal=",",
                encoding=enc
            )

            print(f"Erfolgreich mit {enc}")
            return df

        except Exception:
            pass

    raise Exception("Datei konnte nicht gelesen werden")


def finde_spalte(df, kandidaten):

    for kandidat in kandidaten:
        for spalte in df.columns:
            if kandidat.lower() in spalte.lower():
                return spalte

    raise Exception(
        f"Keine passende Spalte gefunden für {kandidaten}"
    )


def bereinige_stueck(wert):

    try:
        return float(
            str(wert)
            .replace(".", "")
            .replace(",", ".")
        )
    except Exception:
        return 0.0


def vorbereiten(df):

    datum_spalte = finde_spalte(
        df,
        ["Datum","Buchungstag"]
    )

    df["buchungsdatum"] = pd.to_datetime(
        df[datum_spalte],
        dayfirst=True,
        errors="coerce"
    )

    df = df.sort_values(
        "buchungsdatum"
    )

    return df


def erstelle_monatliche_bestaende(df):

    vorgang_spalte = finde_spalte(
        df,
        ["Vorgang"]
    )

    isin_spalte = finde_spalte(
        df,
        ["ISIN"]
    )

    bezeichnung_spalte = finde_spalte(
        df,
        ["Wertpapier", "Bezeichnung"]
    )

    stueck_spalte = finde_spalte(
        df,
        ["Stück", "Anzahl"]
    )

    start = df["buchungsdatum"].min()
    ende = df["buchungsdatum"].max()

    monate = pd.date_range(
        start=start,
        end=ende,
        freq="M"
    )

    ergebnis = []

    for monat in monate:

        bestand = defaultdict(float)

        transaktionen = df[
            df["buchungsdatum"] <= monat
        ]

        namen = {}

        for _, row in transaktionen.iterrows():

            isin = str(row[isin_spalte]).strip()
            vorgang = str(row[vorgang_spalte]).strip()

            stueck = bereinige_stueck(
                row[stueck_spalte]
            )

            namen[isin] = str(
                row[bezeichnung_spalte]
            )

            if vorgang in [
                "Kauf",
                "WP-Einlage"
            ]:
                bestand[isin] += stueck

            elif vorgang in [
                "Verkauf",
                "WP-Entnahme"
            ]:
                bestand[isin] -= stueck

        for isin, stueck in bestand.items():

            if abs(stueck) < 0.00001:
                continue

            ergebnis.append(
                {
                    "monat": monat.date(),
                    "isin": isin,
                    "wertpapier": namen[isin],
                    "bestand": round(stueck, 6)
                }
            )

    return pd.DataFrame(ergebnis)


def main():

    if not Path(CSV_DATEI).exists():
        print(f"Datei fehlt: {CSV_DATEI}")
        return

    Path("output").mkdir(
        exist_ok=True
    )

    df = lese_csv(CSV_DATEI)

    print("\nGefundene Spalten:")
    for c in df.columns:
        print(c)

    df = vorbereiten(df)

    monatliche_bestaende = (
        erstelle_monatliche_bestaende(df)
    )

    monatliche_bestaende.to_csv(
        OUTPUT_DATEI,
        sep=";",
        decimal=",",
        index=False
    )

    print("\nDatei erstellt:")
    print(OUTPUT_DATEI)

    print("\nLetzter Monat:")
    print(
        monatliche_bestaende[
            monatliche_bestaende["monat"]
            ==
            monatliche_bestaende["monat"].max()
        ]
        .sort_values("wertpapier")
        .tail(20)
    )


if __name__ == "__main__":
    main()