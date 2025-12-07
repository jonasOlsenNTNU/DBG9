# src/dashboard/ui/frontier_view.py
from __future__ import annotations

import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas  # noqa: F401
from ..utils.load_css import load_css


def _estimate_frontier(df: pd.DataFrame, quantile: float = 0.1) -> pd.DataFrame:
    """
    Very simple 'frontier' estimate: for each decile of port traffic,
    take the quantile of CO₂ and then fit a line through those points.
    """
    sub = df[["port_traffic", "co2"]].dropna()
    if sub.empty:
        return pd.DataFrame(columns=["port_traffic", "frontier_co2"])

    sub = sub.sort_values("port_traffic")
    sub["bin"] = pd.qcut(sub["port_traffic"], q=min(10, len(sub)), duplicates="drop")

    agg = sub.groupby("bin").agg(
        port_traffic=("port_traffic", "median"),
        frontier_co2=("co2", lambda x: x.quantile(quantile)),
    )
    return agg.reset_index(drop=True)


def create_efficiency_frontier(
        df: pd.DataFrame,
        year: int,
        quantile: float = 0.1,
) -> pn.Column:
    """
    Scatter of port traffic vs CO₂ with a simple quantile-based frontier line.
    """
    sub = df[df["year"] == year].copy()
    if sub.empty:
        return pn.Column(f"No data for {year}.")

    frontier = _estimate_frontier(sub, quantile=quantile)

    scatter = sub.hvplot.scatter(
        x="port_traffic",
        y="co2",
        color="maritime_tier",
        hover_cols=["country"],
        xlabel="Port traffic (TEU)",
        ylabel="Total CO₂ (Mt)",
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
        )
        plot = scatter * line
    else:
        plot = scatter

    return pn.Column(
        pn.pane.HoloViews(plot, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )



def create_frontier_tab(df: pd.DataFrame) -> pn.Column:
    load_css("main_view.css")

    years = sorted(df["year"].unique())
    year_select = pn.widgets.IntSlider(
        name="Year",
        start=min(years),
        end=max(years),
        value=max(years),
    )
    quantile_select = pn.widgets.FloatSlider(
        name="Frontier quantile",
        start=0.05,
        end=0.3,
        step=0.05,
        value=0.1,
    )

    @pn.depends(year_select.param.value, quantile_select.param.value)
    def _view(year, q):
        return create_efficiency_frontier(df, year=int(year), quantile=float(q))

    header = pn.pane.Markdown(
        """
# Efficiency frontier

Who sits closest to the **best-practice emissions line** for a given port traffic level?
The frontier highlights what is technically achievable today for similar economies.
        """,
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )

    controls = pn.Row(
        year_select,
        quantile_select,
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