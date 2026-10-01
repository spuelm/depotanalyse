from pathlib import Path
import pandas as pd

# --------------------------------------------------
# Pfade
# --------------------------------------------------

BASE_DIR = Path(__file__).parent

TRANSACTIONS_FILE = BASE_DIR / "data" / "Wertpapiertransaktionen.csv"
WERTPAPIERE_FILE = BASE_DIR / "config" / "wertpapiere.csv"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# Konfiguration
# --------------------------------------------------

KAUF = "Kauf"
VERKAUF = "Verkauf"
WP_EINLAGE = "WP-Einlage"
WP_ENTNAHME = "WP-Entnahme"

RELEVANTE_VORGAENGE = [
    KAUF,
    VERKAUF,
    WP_EINLAGE,
    WP_ENTNAHME
]

# --------------------------------------------------
# Hilfsfunktion
# --------------------------------------------------

def euro_to_float(value):

    if pd.isna(value):
        return 0.0

    value = str(value).strip()

    if value == "":
        return 0.0

    value = (
        value
        .replace(".", "")
        .replace(",", ".")
    )

    try:
        return float(value)
    except:
        return 0.0


# --------------------------------------------------
# Wertpapierliste laden
# --------------------------------------------------

print("Lade Wertpapierliste...")

wp_liste = pd.read_csv(
    WERTPAPIERE_FILE,
    sep=";"
)

wp_liste["isin"] = (
    wp_liste["isin"]
    .astype(str)
    .str.strip()
)

wp_liste["aktiv"] = pd.to_numeric(
    wp_liste["aktiv"],
    errors="coerce"
).fillna(0)

aktive_isins = set(
    wp_liste.loc[
        wp_liste["aktiv"] == 1,
        "isin"
    ]
)

print(f"Aktive Wertpapiere: {len(aktive_isins)}")

# --------------------------------------------------
# Transaktionen laden
# --------------------------------------------------

print("Lade DKB Export...")

df = pd.read_csv(
    TRANSACTIONS_FILE,
    sep=";",
    encoding="utf-16"
)

df["ISIN"] = (
    df["ISIN"]
    .astype(str)
    .str.strip()
)

# nur aktive Isins
df = df[df["ISIN"].isin(aktive_isins)]

# nur relevante Vorgänge
df = df[
    df["Vorgang"].isin(
        RELEVANTE_VORGAENGE
    )
]

print(f"Relevante Transaktionen: {len(df)}")

# --------------------------------------------------
# Datum
# --------------------------------------------------

df["Buchungstag"] = pd.to_datetime(
    df["Buchungstag"],
    format="%d.%m.%Y",
    errors="coerce"
)

df = df.dropna(
    subset=["Buchungstag"]
)

# --------------------------------------------------
# Zahlenfelder
# --------------------------------------------------

df["Stück / Nennwert"] = (
    df["Stück / Nennwert"]
    .astype(str)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
)

df["Stück / Nennwert"] = pd.to_numeric(
    df["Stück / Nennwert"],
    errors="coerce"
).fillna(0)

df["Soll_float"] = df["Soll"].apply(
    euro_to_float
)

df["Haben_float"] = df["Haben"].apply(
    euro_to_float
)

# --------------------------------------------------
# Aktuelle Bestände
# --------------------------------------------------

print("Berechne aktuelle Bestände...")

bestandsdaten = []

for isin in sorted(aktive_isins):

    wp = df[df["ISIN"] == isin]

    bestand = 0

    for _, row in wp.iterrows():

        if row["Vorgang"] in [KAUF, WP_EINLAGE]:
            bestand += row["Stück / Nennwert"]

        elif row["Vorgang"] in [VERKAUF, WP_ENTNAHME]:
            bestand -= row["Stück / Nennwert"]

    if len(wp) > 0:

        bestandsdaten.append(
            {
                "isin": isin,
                "wertpapier": wp.iloc[0]["Wertpapier"],
                "bestand": round(bestand, 3),
            }
        )

bestandsliste = pd.DataFrame(
    bestandsdaten
)

bestandsliste.sort_values(
    "wertpapier"
).to_csv(
    OUTPUT_DIR / "bestandsliste.csv",
    sep=";",
    decimal=",",
    index=False
)

# --------------------------------------------------
# Monatliche Bestände
# --------------------------------------------------

print("Berechne Monatsbestände...")

start = df["Buchungstag"].min()
ende = df["Buchungstag"].max()

print(f"Zeitraum: {start.date()} bis {ende.date()}")

monate = pd.date_range(
    start=start,
    end=ende,
    freq="M"
)

monatsdaten = []

for monat in monate:

    trans_bis_monat = df[
        df["Buchungstag"] <= monat
    ]

    for isin in aktive_isins:

        wp = trans_bis_monat[
            trans_bis_monat["ISIN"] == isin
        ]

        if wp.empty:
            continue

        bestand = 0.0
        investiert = 0.0

        for _, row in wp.iterrows():

            if row["Vorgang"] in [KAUF, WP_EINLAGE]:

                bestand += row["Stück / Nennwert"]
                investiert += row["Soll_float"]

            elif row["Vorgang"] in [VERKAUF, WP_ENTNAHME]:

                bestand -= row["Stück / Nennwert"]
                investiert -= row["Haben_float"]

        monatsdaten.append(
            {
                "monat": monat.strftime("%Y-%m"),
                "isin": isin,
                "wertpapier": wp.iloc[0]["Wertpapier"],
                "bestand": round(bestand, 3),
                "investiert": round(investiert, 2),
            }
        )

historie_df = pd.DataFrame(
    monatsdaten
)

print(
    f"Monatseinträge: {len(historie_df)}"
)

historie_df.to_csv(
    OUTPUT_DIR / "monatsbestaende.csv",
    sep=";",
    decimal=",",
    index=False
)

# --------------------------------------------------
# Cashflow pro Monat
# --------------------------------------------------

cashflow = []

for monat in monate:

    monats_df = df[
        (df["Buchungstag"].dt.year == monat.year)
        &
        (df["Buchungstag"].dt.month == monat.month)
    ]

    einzahlungen = monats_df.loc[
        monats_df["Vorgang"].isin(
            [KAUF, WP_EINLAGE]
        ),
        "Soll_float"
    ].sum()

    auszahlungen = monats_df.loc[
        monats_df["Vorgang"].isin(
            [VERKAUF, WP_ENTNAHME]
        ),
        "Haben_float"
    ].sum()

    cashflow.append(
        {
            "monat": monat.strftime("%Y-%m"),
            "einzahlungen": round(einzahlungen, 2),
            "auszahlungen": round(auszahlungen, 2),
            "netto": round(
                einzahlungen - auszahlungen,
                2
            )
        }
    )

cashflow_df = pd.DataFrame(
    cashflow
)

cashflow_df.to_csv(
    OUTPUT_DIR / "cashflow_monatlich.csv",
    sep=";",
    decimal=",",
    index=False
)

print()
print("Fertig")
print(bestandsliste.head())