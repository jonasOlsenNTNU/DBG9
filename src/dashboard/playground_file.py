import pandas as pd
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DATA_PATH = DATA_DIR / "port_traffic_data.csv"

COUNTRY_COL = "Country Name"
CODE_COL = "Country Code"


OUTPUT_PATH = DATA_DIR / "port_traffic_relevant_countries.csv"

def main():

    df_raw = pd.read_csv(DATA_PATH)
    print("Raw shape:", df_raw.shape)
    print("Columns:", df_raw.columns.tolist()[:10], "...")

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


    latest_year = df_long["year"].max()
    df_latest = df_long[df_long["year"] == latest_year]

    print(f"\nLatest year in dataset: {latest_year}")
    print("Number of countries with data in latest year:", df_latest[COUNTRY_COL].nunique())


    top10 = df_latest.nlargest(10, "port_traffic")
    bottom10 = df_latest.nsmallest(10, "port_traffic")

    print("\n=== Top 10 maritime countries (by port traffic) ===")
    print(top10[[COUNTRY_COL, "port_traffic"]].to_string(index=False))

    print("\n=== Bottom 10 countries with (non-zero) port traffic ===")
    print(bottom10[[COUNTRY_COL, "port_traffic"]].to_string(index=False))


    relevant_countries = sorted(
        set(top10[COUNTRY_COL]).union(bottom10[COUNTRY_COL])
    )

    df_relevant = df_long[df_long[COUNTRY_COL].isin(relevant_countries)]

    print("\nRelevant countries:", relevant_countries)
    print("\nTime coverage for relevant countries:")
    coverage = df_relevant.groupby(COUNTRY_COL)["year"].agg(["min", "max", "count"])
    print(coverage)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_relevant.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved filtered data for relevant countries to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
