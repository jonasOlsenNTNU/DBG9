import pandas as pd
import panel as pn
import hvplot.pandas  # important
from pathlib import Path

pn.extension()  # basic extension

ROOT = Path(__file__).resolve().parents[2]  # .../DBG9
DATA_DIR = ROOT / "data"
PORT_PATH = DATA_DIR / "port_traffic_data.csv"
CO2_PATH = DATA_DIR / "owid-co2-data.csv"

COUNTRY_COL = "Country Name"
CODE_COL = "Country Code"

def load_port_long():
    df_raw = pd.read_csv(PORT_PATH, skiprows=4)
    year_cols = [c for c in df_raw.columns if c.isdigit()]

    df_long = df_raw.melt(
        id_vars=[COUNTRY_COL, CODE_COL],
        value_vars=year_cols,
        var_name="year",
        value_name="port_traffic",
    )

    df_long["year"] = df_long["year"].astype(int)
    df_long = df_long.dropna(subset=["port_traffic"])
    df_long = df_long[df_long["port_traffic"] > 0]
    df_long = df_long[df_long["year"].between(2000, 2024)]
    return df_long

def load_co2():
    df = pd.read_csv(CO2_PATH)
    df = df[["iso_code", "year", "co2"]]
    df = df.dropna(subset=["co2"])
    df["year"] = df["year"].astype(int)
    df = df[df["year"].between(2000, 2024)]
    return df

def get_top_bottom_codes(df_port):
    latest_year = df_port["year"].max()
    df_latest = df_port[df_port["year"] == latest_year]
    top10 = df_latest.nlargest(10, "port_traffic")
    bottom10 = df_latest.nsmallest(10, "port_traffic")
    top_codes = top10[CODE_COL].tolist()
    bottom_codes = bottom10[CODE_COL].tolist()
    return top_codes, bottom_codes

def build_group_timeseries(df_port, df_co2, iso_codes):
    port_group = (
        df_port[df_port[CODE_COL].isin(iso_codes)]
        .groupby("year", as_index=False)["port_traffic"]
        .sum()
    )
    co2_group = (
        df_co2[df_co2["iso_code"].isin(iso_codes)]
        .groupby("year", as_index=False)["co2"]
        .sum()
    )
    df_merged = pd.merge(port_group, co2_group, on="year", how="inner")
    df_merged["co2_norm"] = df_merged["co2"] / df_merged["co2"].max()
    df_merged["port_norm"] = df_merged["port_traffic"] / df_merged["port_traffic"].max()
    return df_merged

def make_group_plot(df_group, title):
    co2_curve = df_group.hvplot.line(x="year", y="co2_norm", label="CO₂ (index)")
    port_curve = df_group.hvplot.line(
        x="year", y="port_norm", label="Container port traffic (index)", line_dash="dashed"
    )
    return (co2_curve * port_curve).opts(title=title, xlabel="Year", ylabel="Index (0–1)")

df_port = load_port_long()
df_co2 = load_co2()
top_codes, bottom_codes = get_top_bottom_codes(df_port)

top_ts = build_group_timeseries(df_port, df_co2, top_codes)
bottom_ts = build_group_timeseries(df_port, df_co2, bottom_codes)

top_plot = make_group_plot(
    top_ts, "Top 10 maritime countries – CO₂ vs container port traffic (2000–2024)"
)
bottom_plot = make_group_plot(
    bottom_ts, "Bottom 10 maritime countries – CO₂ vs container port traffic (2000–2024)"
)

maritime_group_section = pn.Column(
    "## CO₂ vs container port traffic – Top 10 vs Bottom 10 (2000–2024)",
    top_plot,
    bottom_plot,
)

maritime_group_section.servable()
