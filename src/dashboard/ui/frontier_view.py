from __future__ import annotations

import pandas as pd
import panel as pn
from ..utils.load_css import load_css
from .plot_generator import ACCENT_PALETTE


def _estimate_frontier(
        df: pd.DataFrame,
        co2_col: str = "co2",
        quantile: float = 0.1,
) -> pd.DataFrame:
    sub = df[["port_traffic", co2_col]].dropna()
    if sub.empty:
        return pd.DataFrame(columns=["port_traffic", "frontier_co2"])

    sub = sub.sort_values("port_traffic")
    sub["bin"] = pd.qcut(sub["port_traffic"], q=min(10, len(sub)), duplicates="drop")

    agg = sub.groupby("bin").agg(
        port_traffic=("port_traffic", "median"),
        frontier_co2=(co2_col, lambda x: x.quantile(quantile)),
    )
    return agg.reset_index(drop=True)


def create_efficiency_frontier(
        df: pd.DataFrame,
        year: int,
        quantile: float = 0.1,
        co2_col: str = "co2",
) -> pn.Column:
    sub = df[df["year"] == year].copy()
    if sub.empty:
        return pn.Column(f"No data for {year}.")

    y_label = "Total CO₂ (Mt)" if co2_col == "co2" else "Maritime CO₂ (Mt)"

    frontier = _estimate_frontier(sub, co2_col=co2_col, quantile=quantile)

    scatter = sub.hvplot.scatter(
        x="port_traffic",
        y=co2_col,
        color="maritime_tier",
        cmap="Accent",
        hover_cols=["country"],
        xlabel="Port traffic (TEU)",
        ylabel=y_label,
        title=f"Efficiency frontier – {year}",
        responsive=True,
        min_height=400,
    )

    if not frontier.empty:
        line = frontier.hvplot.line(
            x="port_traffic",
            y="frontier_co2",
            line_width=2,
            alpha=0.8,
            color="#666666",
        )
        plot = scatter * line
    else:
        plot = scatter

    return pn.Column(pn.pane.HoloViews(plot, sizing_mode="stretch_width"))


def create_frontier_tab(df: pd.DataFrame) -> pn.Column:
    load_css("main_view.css")
    years = sorted(df["year"].unique())
    year_select = pn.widgets.IntSlider(
        name="Year",
        start=min(years),
        end=max(years),
        value=max(years),
    )
    quantile_select = pn.widgets.DiscreteSlider(
        name="Frontier quantile",
        options=[0.05, 0.1, 0.25],
        value=0.1,
    )
    co2_select = pn.widgets.Select(
        name="Emission variable",
        options={
            "Total CO₂": "co2",
            "Maritime CO₂": "maritime_co2",
        },
        value="co2",
        width=220,
    )

    @pn.depends(
        year_select.param.value,
        quantile_select.param.value,
        co2_select.param.value,
    )
    def _view(year, q, co2_col):
        return create_efficiency_frontier(
            df,
            year=int(year),
            quantile=float(q),
            co2_col=co2_col,
        )

    header = pn.pane.Markdown(
        "## Efficiency frontier\n"
        "Who is closest to the 'best practice' line for a given CO₂ measure?",
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )

    controls = pn.Row(
        year_select,
        quantile_select,
        co2_select,
        sizing_mode="stretch_width",
    )

    content_card = pn.Column(
        controls,
        _view,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    return pn.Column(
        header,
        content_card,
        sizing_mode="stretch_width",
        css_classes=["story-layout"],
    )
