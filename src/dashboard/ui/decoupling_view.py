from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
import panel as pn
import holoviews as hv
import hvplot.pandas  # noqa: F401

pn.extension()


def _compute_cagr(group: pd.DataFrame, col: str, start: int, end: int) -> float:
    g = group.set_index("year")
    if start not in g.index or end not in g.index:
        return np.nan
    v0 = g.at[start, col]
    v1 = g.at[end, col]
    if pd.isna(v0) or pd.isna(v1) or v0 <= 0 or v1 <= 0 or end <= start:
        return np.nan
    return (v1 / v0) ** (1.0 / (end - start)) - 1.0


def _build_decoupling_frame(df: pd.DataFrame, period: Tuple[int, int]) -> pd.DataFrame:
    start, end = period
    subset = df[(df["year"] >= start) & (df["year"] <= end)].copy()

    records: list[dict] = []
    for iso, g in subset.groupby("iso_code"):
        g = g.sort_values("year")
        if g["year"].min() > start or g["year"].max() < end:
            continue

        port_cagr = _compute_cagr(g, "port_traffic", start, end)
        co2_cagr = _compute_cagr(g, "co2", start, end)
        if np.isnan(port_cagr) or np.isnan(co2_cagr):
            continue

        baseline = g[g["year"] == start].iloc[0]

        records.append(
            {
                "iso_code": iso,
                "country": baseline["country"],
                "maritime_tier": baseline.get("maritime_tier", "unknown"),
                "port_cagr": port_cagr * 100.0,
                "co2_cagr": co2_cagr * 100.0,
                "decoupling_index": (port_cagr - co2_cagr) * 100.0,
                "baseline_co2": baseline["co2"],
            }
        )

    return pd.DataFrame.from_records(records)


def _decoupling_insights(
        df: pd.DataFrame, period: Tuple[int, int], tiers: List[str] | None
) -> pn.pane.Markdown:
    summary = _build_decoupling_frame(df, period)
    if tiers:
        summary = summary[summary["maritime_tier"].isin(tiers)]

    if summary.empty:
        return pn.pane.Markdown("**Key insights**\n\nNo data for current filters.")

    strong = summary[(summary["port_cagr"] > 0) & (summary["co2_cagr"] < 0)]
    weak = summary[
        (summary["port_cagr"] > 0)
        & (summary["co2_cagr"].between(0, summary["port_cagr"]))
        ]
    brown = summary[
        (summary["port_cagr"] > 0) & (summary["co2_cagr"] > summary["port_cagr"])
        ]

    best = summary.sort_values("decoupling_index", ascending=False).head(3)
    worst = summary.sort_values("decoupling_index", ascending=True).head(3)

    def _list_countries(df_, prefix: str) -> str:
        if df_.empty:
            return ""
        names = ", ".join(df_["country"].tolist())
        return f"- {prefix}: {names}\n"

    text = (
        "### Key insights\n\n"
        f"- Strong decouplers (port ↑, CO₂ ↓): **{len(strong)}** countries\n"
        f"- Weak/relative decouplers: **{len(weak)}** countries\n"
        f"- Brown growth (port ↑, CO₂ ↑ faster): **{len(brown)}** countries\n\n"
        f"{_list_countries(best, 'Best decoupling (top 3)')}"
        f"{_list_countries(worst, 'Worst decoupling (bottom 3)')}"
    )
    return pn.pane.Markdown(text)


def create_decoupling_scatter(
        df: pd.DataFrame,
        period: Tuple[int, int] = (2015, 2022),
        maritime_tier_filter: list[str] | None = None,
) -> pn.Column:
    """
    Scatter: X = port CAGR (%), Y = CO₂ CAGR (%), color by maritime tier, size by baseline CO₂.
    Top section of the Decoupling Explorer tab.
    """
    years = sorted(df["year"].unique())
    start_year = max(min(years), 2000)
    end_year = max(years)

    if maritime_tier_filter is None:
        maritime_tier_filter = sorted(df["maritime_tier"].dropna().unique())

    year_slider = pn.widgets.IntRangeSlider(
        name="Period (CAGR)",
        start=start_year,
        end=end_year,
        value=period,
        step=1,
    )

    tier_options = sorted(df["maritime_tier"].dropna().unique())
    tier_select = pn.widgets.CheckButtonGroup(
        name="Maritime tiers",
        options=tier_options,
        value=maritime_tier_filter,
        button_type="primary",
    )

    @pn.depends(year_slider.param.value, tier_select.param.value)
    def scatter_view(period_val, tiers):
        summary = _build_decoupling_frame(df, tuple(period_val))
        if tiers:
            summary = summary[summary["maritime_tier"].isin(tiers)]

        if summary.empty:
            return pn.pane.Markdown("No countries with complete data for this period.")

        pts = summary.hvplot.scatter(
            x="port_cagr",
            y="co2_cagr",
            color="maritime_tier",
            size="baseline_co2",
            hover_cols=["country", "decoupling_index", "baseline_co2"],
            xlabel="Port traffic CAGR (%)",
            ylabel="CO₂ CAGR (%)",
            title="Port vs CO₂ growth (CAGR)",
            width=1350,   # <–– wider
            height=600,   # <–– taller
            responsive=False,
        )

        x_min = float(summary["port_cagr"].min())
        x_max = float(summary["port_cagr"].max())
        y_min = float(summary["co2_cagr"].min())
        y_max = float(summary["co2_cagr"].max())
        lo = min(x_min, y_min, -5)
        hi = max(x_max, y_max, 5)
        xs = np.linspace(lo, hi, 50)

        diag = hv.Curve((xs, xs)).opts(line_dash="dashed", line_width=1, line_alpha=0.7)
        hor = hv.Curve((xs, np.zeros_like(xs))).opts(
            line_dash="dotted", line_width=1, line_alpha=0.7
        )

        return (pts * diag * hor).opts(legend_position="top_right")

    @pn.depends(year_slider.param.value, tier_select.param.value)
    def insights_view(period_val, tiers):
        return _decoupling_insights(df, tuple(period_val), list(tiers))

    return pn.Column(
        pn.pane.Markdown("## Decoupling explorer\nHow port growth relates to CO₂ growth."),
        pn.Row(year_slider, tier_select),
        scatter_view,
        insights_view,
        sizing_mode="stretch_width",
    )


def create_decoupling_timeline(df: pd.DataFrame, iso_code: str) -> pn.Column:
    """
    Timeline for a single country:
    - Port traffic and CO₂ indexed to first available year = 100.
    - X-axis restricted to that country’s actual data range.
    """
    country_df = df[df["iso_code"] == iso_code].sort_values("year")
    if country_df.empty:
        return pn.Column(f"No data for {iso_code}")

    base = country_df.iloc[0]
    port_base = base["port_traffic"]
    co2_base = base["co2"]

    if port_base <= 0 or co2_base <= 0:
        return pn.Column(
            f"Cannot index series for {country_df['country'].iloc[0]} (non-positive base)."
        )

    country_df = country_df.assign(
        port_index=country_df["port_traffic"] / port_base * 100.0,
        co2_index=country_df["co2"] / co2_base * 100.0,
    )

    x_min = int(country_df["year"].min())
    x_max = int(country_df["year"].max())

    curves = country_df.hvplot.line(
        x="year",
        y=["port_index", "co2_index"],
        ylabel="Index (first year = 100)",
        xlabel="Year",
        title=f"Port vs CO₂ over time – {country_df['country'].iloc[0]}",
        width=1000,
        height=500,
        responsive=False,
    )

    curves = curves.redim.range(year=(2000, x_max)).opts(shared_axes=False)

    return pn.Column(curves, sizing_mode="stretch_both")


def create_decoupling_tab(df: pd.DataFrame) -> pn.Column:
    """
    Full Decoupling Explorer tab:
    - Top: filters + scatter + key insights
    - Bottom: Country timeline selector + big Port vs CO₂ over time graph.
    """
    # Top section: title + filters + scatter + key insights
    scatter_section = create_decoupling_scatter(df)

    # Country selector for the timeline
    countries = sorted(df["country"].unique())
    default_country = "Norway" if "Norway" in countries else countries[0]

    country_select = pn.widgets.Select(
        name="Country",
        options=countries,
        value=default_country,
        width=250,
    )

    @pn.depends(country_select.param.value)
    def timeline_view(country_name):
        if not country_name:
            return pn.pane.Markdown("Select a country to see its timeline.")
        iso_codes = df.loc[df["country"] == country_name, "iso_code"].unique()
        if len(iso_codes) == 0:
            return pn.pane.Markdown(f"No ISO code found for {country_name}.")
        return create_decoupling_timeline(df, iso_codes[0])

    # Bottom section: heading + dropdown above the big graph
    timeline_block = pn.Column(
        pn.Spacer(height=100),  # padding above
        pn.pane.Markdown("### Country timeline"),
        country_select,
        timeline_view,
        sizing_mode="stretch_both",
    )

    return pn.Column(
        scatter_section,
        timeline_block,
        sizing_mode="stretch_both",
    )
