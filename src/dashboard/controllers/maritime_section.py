# src/dashboard/controllers/maritime_section.py

from pathlib import Path
import pandas as pd
import panel as pn
import numpy as np
TOP_COLOR = "#004c6d"
BOTTOM_COLOR = "#2a9d8f"
PORT_COLOR = "#e76f51"
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
def interpret_correlation(r: float) -> str:
    """Return a short human-readable interpretation for a Pearson r."""
    if r > 0.7:
        return "This indicates a **strong positive correlation** between CO₂ and port traffic."
    if r > 0.4:
        return "This indicates a **moderate positive correlation** between CO₂ and port traffic."
    if r > 0.2:
        return "This indicates a **weak positive correlation** between CO₂ and port traffic."
    if r > -0.2:
        return "This indicates **no clear linear correlation**."
    if r > -0.4:
        return "This indicates a **weak negative correlation** between CO₂ and port traffic."
    if r > -0.7:
        return "This indicates a **moderate negative correlation** between CO₂ and port traffic."
    return "This indicates a **strong negative correlation** between CO₂ and port traffic."


def build_correlation_section(df_group: pd.DataFrame, group_name: str):
    """
    Build a correlation card for one group:
      - numeric Pearson correlation
      - scatter plot CO₂ vs port traffic
      - regression line
      - short interpretation text underneath
    """
    if df_group.empty:
        return pn.pane.Markdown(f"**No data available for {group_name}.**")

    # Use raw columns if they exist, otherwise fall back to normalized.
    if "port_traffic" in df_group.columns:
        x = df_group["port_traffic"]
    else:
        x = df_group["port_norm"]

    if "co2" in df_group.columns:
        y = df_group["co2"]
    else:
        y = df_group["co2_norm"]

    # Compute correlation (works the same on normalized or raw values)
    corr = x.corr(y)

    # DataFrame for plotting
    scatter_df = pd.DataFrame({"port_traffic": x, "co2": y})

    scatter = scatter_df.hvplot.scatter(
        x="port_traffic",
        y="co2",
        xlabel="Container port traffic (TEU or index)",
        ylabel="Total CO₂ (Mt or index)",
        title=f"{group_name} — CO₂ vs port traffic",
        size=7,
        color=TOP_COLOR,   # samme blå som de andre grafene
    )

    # Regression line – egen dataframe med kolonnenavn
    x_sorted = np.linspace(x.min(), x.max(), 50)
    coef = np.polyfit(x, y, 1)
    y_hat = np.poly1d(coef)(x_sorted)
    reg_df = pd.DataFrame({"port_traffic": x_sorted, "co2": y_hat})

    reg_line = reg_df.hvplot.line(
        x="port_traffic",
        y="co2",
        color=PORT_COLOR,   # samme oransje som containerlinja
        line_width=2,
        alpha=0.8,
        label="Regression line",
    )

    combined = (scatter * reg_line).opts(
        height=320,
        shared_axes=False,
        show_grid=True,
        toolbar=None,       # ingen toolbar, matcher resten
    )

    text = pn.pane.Markdown(
        f"""
**Pearson correlation:** `{corr:.3f}`  

{interpret_correlation(corr)}
""",
        sizing_mode="stretch_width",
    )

    # Graf øverst, tekst under – matcher stilen i resten av dashboardet
    return pn.Column(
        combined,
        text,
        sizing_mode="stretch_width",
    )



def create_maritime_group_section(top_iso, bottom_iso):
    """
    Build the full maritime section with two cards:

      A) Time series card:
         - Top 10: CO₂ vs container port traffic (index, 2000–2024)
         - Bottom 10: CO₂ vs container port traffic (index, 2000–2024)

      B) Correlation card:
         - Scatter plots and Pearson r for Top 10 and Bottom 10
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

    # ---- Card A: time series ----
    time_series_card = pn.Column(
        "## CO₂ vs container port traffic – Top 10 vs Bottom 10 (2000–2024)",
        top_plot,
        bottom_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    # ---- Card B: correlation analysis ----
    corr_top = build_correlation_section(top_ts, "Top 10 maritime economies")
    corr_bottom = build_correlation_section(bottom_ts, "Bottom 10 maritime economies")

    corr_card = pn.Column(
        "## Correlation between maritime activity and CO₂ emissions",
        pn.pane.Markdown(
            "We compute Pearson correlations and show scatter plots with regression "
            "lines to quantify how strongly container port traffic is linked to CO₂ "
            "emissions for each group."
        ),
        corr_top,
        corr_bottom,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    # Return both cards as two stacked sections in the storyboard
    return pn.Column(
        time_series_card,
        corr_card,
        sizing_mode="stretch_width",
    )



