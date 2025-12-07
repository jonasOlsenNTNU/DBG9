# src/dashboard/ui/frontier_view.py
from __future__ import annotations

import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas  # noqa: F401


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

    return pn.Column(pn.pane.HoloViews(plot, sizing_mode="stretch_both"))


def create_frontier_tab(df: pd.DataFrame) -> pn.Column:
    years = sorted(df["year"].unique())
    year_select = pn.widgets.IntSlider(name="Year", start=min(years), end=max(years), value=max(years))
    quantile_select = pn.widgets.DiscreteSlider(
        name="Frontier quantile",
        options=[0.05, 0.1, 0.25],
        value=0.1,
    )

    @pn.depends(year_select.param.value, quantile_select.param.value)
    def _view(year, q):
        return create_efficiency_frontier(df, year=int(year), quantile=float(q))

    return pn.Column(
        pn.pane.Markdown("## Efficiency frontier\nWho is closest to the 'best practice' line?"),
        pn.Row(year_select, quantile_select),
        _view,
        sizing_mode="stretch_both",
    )

