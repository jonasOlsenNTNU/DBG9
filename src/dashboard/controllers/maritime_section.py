from pathlib import Path
import pandas as pd
import panel as pn
import numpy as np
from bokeh.plotting import figure
from idna import ulabel

TOP_COLOR = "#004c6d"
BOTTOM_COLOR = "#2a9d8f"
PORT_COLOR = "#e76f51"

ROOT = Path(__file__).resolve().parents[3]
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

def create_trade_forecast_section(top_iso, bottom_iso, horizon: int = 3):
    df_port = load_port_long()
    df_co2 = load_co2()

    group_map = {
        "Top 10 maritime economies": top_iso,
        "Bottom 10 maritime economies": bottom_iso,
    }

    group_select = pn.widgets.RadioButtonGroup(
        name="Group",
        options=list(group_map.keys()),
        value="Top 10 maritime economies",
        button_type="default",
    )

    def _view(label: str):
        iso_codes = group_map[label]
        plot, mae_trade = make_trade_forecast_plot(
            df_port, df_co2, iso_codes, label, horizon=horizon
        )

        text = pn.pane.Markdown(
            f"""
### Trade-based CO₂ forecast – {label}

We estimate a simple regression **CO₂ = α + β · port traffic** on historical
data (2000–2024) for this group. Future **port traffic** is extrapolated with
a linear time trend and mapped through the regression to obtain a
**{horizon}-year trade-based CO₂ forecast**.

Backtesting on the last 3 observed years gives a mean absolute error (MAE)
of **{mae_trade:,.1f} Mt** for the trade-based model.
""",
            sizing_mode="stretch_width",
        )

        return pn.Column(text, plot)

    dynamic_panel = pn.bind(_view, label=group_select)

    return pn.Column(
        "## Trade-based CO₂ forecast from container port traffic",
        pn.pane.Markdown(
            "This section links **container port traffic** directly to "
            "**CO₂ emissions**. It complements the pure time-series models "
            "by forecasting CO₂ through a regression on maritime trade volumes."
        ),
        group_select,
        dynamic_panel,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

def build_group_timeseries(df_port, df_co2, iso_codes):
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

def make_trade_forecast_plot(
        df_port: pd.DataFrame,
        df_co2: pd.DataFrame,
        iso_codes,
        group_label: str,
        horizon: int = 3,
):
    ts = build_group_timeseries(df_port, df_co2, iso_codes)
    if ts is None or ts.empty:
        return pn.pane.Markdown("⚠️ No data available for this group."), float("nan")

    ts = ts.sort_values("year").copy()
    ts = ts[ts["year"] >= 2000].copy()
    if ts.empty:
        return pn.pane.Markdown("⚠️ No data from year 2000 onwards."), float("nan")

    years = ts["year"].values.astype(int)
    co2 = ts["co2"].values.astype(float)
    port = ts["port_traffic"].values.astype(float)

    beta, alpha = np.polyfit(port, co2, 1)
    fitted = alpha + beta * port

    port_slope, port_intercept = np.polyfit(years, port, 1)
    last_year = years.max()
    horizon = max(1, horizon)

    future_years = np.arange(last_year + 1, last_year + horizon + 1)
    future_port = port_slope * future_years + port_intercept
    future_co2 = alpha + beta * future_port

    back_h = min(3, len(years))
    if back_h > 0:
        test_mask = years > (last_year - back_h)
        mae_trade = float(np.mean(np.abs(co2[test_mask] - fitted[test_mask])))
    else:
        mae_trade = float("nan")

    plot_df = pd.DataFrame(
        {
            "year": np.concatenate([years, years, future_years]),
            "co2": np.concatenate([co2, fitted, future_co2]),
            "series": (
                    ["History"] * len(years)
                    + ["Trade-based fitted"] * len(years)
                    + ["Trade-based forecast"] * len(future_years)
            ),
        }
    )

    plot_df["forecast_year"] = plot_df["year"]

    color_key = {
        "History": TOP_COLOR if group_label.startswith("Top") else BOTTOM_COLOR,
        "Trade-based fitted": "#f4a261",
        "Trade-based forecast": PORT_COLOR,
    }

    min_year_plot = 2000
    max_year_plot = int(last_year + horizon)

    plot = plot_df.hvplot.line(
        x="forecast_year",
        y="co2",
        by="series",
        line_width=3,
        color_key=color_key,
    ).opts(
        xlabel="Year",
        ylabel="Total CO₂ (Mt)",
        height=320,
        show_grid=True,
        toolbar=None,
        legend_position="top_left",
        xlim=(min_year_plot, max_year_plot),
    )

    return plot, mae_trade






def make_group_plot(df_group, title):
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
        shared_axes=False,
        framewise=True,
        show_grid=True,
        toolbar="disable",
    )
def interpret_correlation(r: float) -> str:

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
    if df_group.empty:
        return pn.pane.Markdown(f"**No data available for {group_name}.**")

    if "port_traffic" in df_group.columns:
        x = df_group["port_traffic"]
    else:
        x = df_group["port_norm"]

    if "co2" in df_group.columns:
        y = df_group["co2"]
    else:
        y = df_group["co2_norm"]

    corr = x.corr(y)

    scatter_df = pd.DataFrame({"port_traffic": x, "co2": y})

    scatter = scatter_df.hvplot.scatter(
        x="port_traffic",
        y="co2",
        xlabel="Container port traffic (TEU or index)",
        ylabel="Total CO₂ (Mt or index)",
        title=f"{group_name} — CO₂ vs port traffic",
        size=7,
        color=TOP_COLOR,
    )

    x_sorted = np.linspace(x.min(), x.max(), 50)
    coef = np.polyfit(x, y, 1)
    y_hat = np.poly1d(coef)(x_sorted)
    reg_df = pd.DataFrame({"port_traffic": x_sorted, "co2": y_hat})

    reg_line = reg_df.hvplot.line(
        x="port_traffic",
        y="co2",
        color=PORT_COLOR,
        line_width=2,
        alpha=0.8,
        label="Regression line",
    )

    combined = (scatter * reg_line).opts(
        height=320,
        shared_axes=False,
        show_grid=True,
        toolbar=None,
    )

    text = pn.pane.Markdown(
        f"""
**Pearson correlation:** `{corr:.3f}`  

{interpret_correlation(corr)}
""",
        sizing_mode="stretch_width",
    )

    return pn.Column(
        combined,
        text,
        sizing_mode="stretch_width",
    )

def make_trade_forecast_plot(
        df_port: pd.DataFrame,
        df_co2: pd.DataFrame,
        iso_codes,
        group_label: str,
        horizon: int = 3,
):
    ts = build_group_timeseries(df_port, df_co2, iso_codes)
    if ts is None or ts.empty:
        return pn.pane.Markdown("⚠️ No data available for this group."), float("nan")


    ts = ts.sort_values("year").copy()
    ts = ts[ts["year"] >= 2000].copy()
    if ts.empty:
        return pn.pane.Markdown("⚠️ No data from year 2000 onwards."), float("nan")

    years = ts["year"].values.astype(int)
    co2 = ts["co2"].values.astype(float)
    port = ts["port_traffic"].values.astype(float)


    beta, alpha = np.polyfit(port, co2, 1)
    fitted = alpha + beta * port


    port_slope, port_intercept = np.polyfit(years, port, 1)
    last_year = int(years.max())
    horizon = max(1, horizon)

    future_years = np.arange(last_year + 1, last_year + horizon + 1)
    future_port = port_slope * future_years + port_intercept
    future_co2 = alpha + beta * future_port

    back_h = min(3, len(years))
    if back_h > 0:
        test_mask = years > (last_year - back_h)
        mae_trade = float(np.mean(np.abs(co2[test_mask] - fitted[test_mask])))
    else:
        mae_trade = float("nan")

    min_year_plot = 2000
    max_year_plot = last_year + horizon

    fig = figure(
        width=800,
        height=320,
        x_range=(min_year_plot, max_year_plot),
        x_axis_label="Year",
        y_axis_label="Total CO₂ (Mt)",
        toolbar_location=None,
    )


    hist_color = TOP_COLOR if group_label.startswith("Top") else BOTTOM_COLOR
    fitted_color = "#f4a261"
    forecast_color = PORT_COLOR

    fig.line(years, co2, line_width=3, color=hist_color, legend_label="History")

    fig.line(years, fitted, line_width=2, color=fitted_color, legend_label="Trade-based fitted")

    fig.line(
        future_years,
        future_co2,
        line_width=3,
        color=forecast_color,
        legend_label="Trade-based forecast",
    )

    fig.legend.location = "top_left"
    fig.legend.click_policy = "hide"

    return fig, mae_trade


def create_maritime_group_section(top_iso, bottom_iso):
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

    time_series_card = pn.Column(
        "## CO₂ vs container port traffic – Top 10 vs Bottom 10 (2000–2024)",
        top_plot,
        bottom_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )


    corr_top = build_correlation_section(top_ts, "Top 10 maritime economies")
    corr_bottom = build_correlation_section(bottom_ts, "Bottom 10 maritime economies")

    corr_card = pn.Column(
        "## Correlation between maritime activity and CO₂ emissions (groups)",
        pn.pane.Markdown(
            "We compute Pearson correlations and show scatter plots with regression "
            "lines to quantify how strongly container port traffic is linked to CO₂ "
            "emissions for the Top 10 and Bottom 10 maritime country groups."
        ),
        corr_top,
        corr_bottom,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )


    countries = (
        load_port_long()[[COUNTRY_COL, CODE_COL]]
        .drop_duplicates()
        .sort_values(COUNTRY_COL)
    )
    iso_to_name = dict(zip(countries[CODE_COL], countries[COUNTRY_COL]))
    valid_iso = sorted(
        set(countries[CODE_COL]) & set(df_co2["iso_code"].unique())
    )
    options = {f"{iso_to_name[iso]} ({iso})": iso for iso in valid_iso}

    country_select = pn.widgets.Select(
        name="Country for port traffic vs CO₂",
        options=options,
        value=next(iter(options.values())) if options else None,
        width=320,
    )

    def _country_ts(iso: str):
        ts = build_country_timeseries(df_port, df_co2, iso)
        name = iso_to_name.get(iso, iso)
        title = f"{name} – CO₂ vs container port traffic (2000–2024)"
        return make_group_plot(ts, title)

    def _country_corr(iso: str):
        ts = build_country_timeseries(df_port, df_co2, iso)
        name = iso_to_name.get(iso, iso)
        return build_correlation_section(ts, name)

    country_ts_panel = pn.bind(_country_ts, iso=country_select)
    country_corr_panel = pn.bind(_country_corr, iso=country_select)

    per_country_card = pn.Column(
        "## Per-country CO₂ vs container port traffic",
        pn.pane.Markdown(
            "Select a country to compare its **container port traffic** with its "
            "total **CO₂ emissions**. Both the time-series plot and the correlation "
            "analysis below update to reflect the selected country."
        ),
        country_select,
        country_ts_panel,
        country_corr_panel,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    return pn.Column(
        time_series_card,
        corr_card,
        per_country_card,
        sizing_mode="stretch_width",
    )

def build_country_timeseries(df_port: pd.DataFrame, df_co2: pd.DataFrame, iso_code: str) -> pd.DataFrame:
    if not iso_code:
        return pd.DataFrame(columns=["year", "co2_norm", "port_norm"])
    return build_group_timeseries(df_port, df_co2, [iso_code])