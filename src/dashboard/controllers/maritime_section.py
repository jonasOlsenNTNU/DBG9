# src/dashboard/controllers/maritime_section.py

from pathlib import Path
import pandas as pd
import panel as pn
import hvplot.pandas  # gir .hvplot på DataFrames/Series

ROOT = Path(__file__).resolve().parents[3]   # .../DBG9
DATA_DIR = ROOT / "data"
PORT_PATH = DATA_DIR / "port_traffic_data.csv"
CO2_PATH = DATA_DIR / "owid-co2-data.csv"

COUNTRY_COL = "Country Name"
CODE_COL = "Country Code"


def load_port_long():
    """Load World Bank container port traffic and return long format."""
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
    """Load OWID CO₂ data for 2000–2024 (total CO₂ per country/year)."""
    df = pd.read_csv(CO2_PATH)
    df = df[["iso_code", "year", "co2"]]
    df = df.dropna(subset=["co2"])
    df["year"] = df["year"].astype(int)
    df = df[df["year"].between(2000, 2024)]
    return df


def build_group_timeseries(df_port, df_co2, iso_codes):
    """
    Build aggregated time series for a given list of ISO country codes:
    - Sum of port traffic per year (TEU)
    - Sum of CO₂ per year (Mt)
    - Normalized 0–1 versions for plotting on the same axis
    """
    if not iso_codes:
        return pd.DataFrame(columns=["year", "co2_norm", "port_norm"])

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

    if df_merged.empty:
        return pd.DataFrame(columns=["year", "co2_norm", "port_norm"])

    df_merged["co2_norm"] = df_merged["co2"] / df_merged["co2"].max()
    df_merged["port_norm"] = df_merged["port_traffic"] / df_merged["port_traffic"].max()
    return df_merged


def make_group_plot(df_group, title):
    """Create a combined line plot of normalized CO₂ and port traffic for a group."""
    if df_group.empty:
        return pn.pane.Markdown(f"**No data available for: {title}**")

    co2_curve = df_group.hvplot.line(
        x="year",
        y="co2_norm",
        label="CO₂ (index)",
        line_width=2,
    )
    port_curve = df_group.hvplot.line(
        x="year",
        y="port_norm",
        label="Container port traffic (index)",
        line_width=2,
        line_dash="dashed",
    )

    overlay = co2_curve * port_curve

    return overlay.opts(
        title=title,
        xlabel="Year",
        ylabel="Index (0–1)",
        height=320,
        xlim=(2000, 2024),
        shared_axes=False,   # ingen zoom-linking til andre plott
        framewise=True,
        show_grid=True,
        toolbar="disable",
    )


def create_maritime_group_section(top_iso, bottom_iso):
    """
    Build the full maritime section with two plots, using the SAME
    Top 10 / Bottom 10 country groups as the OWID-CO₂ storyboard.

    top_iso:    list of ISO3 country codes for Top 10 group
    bottom_iso: list of ISO3 country codes for Bottom 10 group
    """
    df_port = load_port_long()
    df_co2 = load_co2()

    top_ts = build_group_timeseries(df_port, df_co2, top_iso)
    bottom_ts = build_group_timeseries(df_port, df_co2, bottom_iso)

    top_plot = make_group_plot(
        top_ts,
        "Top 10 maritime countries – CO₂ vs container port traffic (2000–2024)",
    )
    bottom_plot = make_group_plot(
        bottom_ts,
        "Bottom 10 maritime countries – CO₂ vs container port traffic (2000–2024)",
    )

    section = pn.Column(
        "## CO₂ vs container port traffic – Top 10 vs Bottom 10 (2000–2024)",
        top_plot,
        bottom_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],  # samme stil som de andre seksjonene
    )
    return section
