# port_traffic_playground.py

import pandas as pd
from pathlib import Path

# --- CONFIG ---
# Hvis denne fila ligger i .../DBG9/dashboard/port_traffic_playground.py
# så er parents[2] = .../DBG9
ROOT = Path(__file__).resolve().parents[2]   # .../DBG9
DATA_DIR = ROOT / "data"
DATA_PATH = DATA_DIR / "port_traffic_data.csv"

COUNTRY_COL = "Country Name"
CODE_COL = "Country Code"

# legg også til denne som mangler i koden din:
OUTPUT_PATH = DATA_DIR / "port_traffic_relevant_countries.csv"

def main():
    # 1) Load raw World Bank-style data (years as columns)
    df_raw = pd.read_csv(DATA_PATH)
    print("Raw shape:", df_raw.shape)
    print("Columns:", df_raw.columns.tolist()[:10], "...")

    # 2) Detect year columns and melt to long format: country, year, port_traffic
    year_cols = [c for c in df_raw.columns if c.isdigit()]
    if not year_cols:
        raise ValueError("No year columns detected (e.g. '2000', '2001', ...). Check your CSV format.")

    df_long = df_raw.melt(
        id_vars=[COUNTRY_COL, CODE_COL],
        value_vars=year_cols,
        var_name="year",
        value_name="port_traffic"
    )

    df_long["year"] = df_long["year"].astype(int)
    df_long = df_long.dropna(subset=["port_traffic"])
    df_long = df_long[df_long["port_traffic"] > 0]

    print("\nLong format sample:")
    print(df_long.head())

    # 3) Find latest year with data
    latest_year = df_long["year"].max()
    df_latest = df_long[df_long["year"] == latest_year]

    print(f"\nLatest year in dataset: {latest_year}")
    print("Number of countries with data in latest year:", df_latest[COUNTRY_COL].nunique())

    # 4) Top 10 and bottom 10 countries by port_traffic in latest year
    top10 = df_latest.nlargest(10, "port_traffic")
    bottom10 = df_latest.nsmallest(10, "port_traffic")

    print("\n=== Top 10 maritime countries (by port traffic) ===")
    print(top10[[COUNTRY_COL, "port_traffic"]].to_string(index=False))

    print("\n=== Bottom 10 countries with (non-zero) port traffic ===")
    print(bottom10[[COUNTRY_COL, "port_traffic"]].to_string(index=False))

    # 5) Keep only relevant countries (top + bottom 10) for full time series
    relevant_countries = sorted(
        set(top10[COUNTRY_COL]).union(bottom10[COUNTRY_COL])
    )

    df_relevant = df_long[df_long[COUNTRY_COL].isin(relevant_countries)]

    print("\nRelevant countries:", relevant_countries)
    print("\nTime coverage for relevant countries:")
    coverage = df_relevant.groupby(COUNTRY_COL)["year"].agg(["min", "max", "count"])
    print(coverage)

    # 6) Save filtered dataset for use in your Panel app / further analysis
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_relevant.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved filtered data for relevant countries to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
