from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas
from ..utils.load_css import load_css


def create_sectoral_breakdown(
        df: pd.DataFrame,
        selection: str,
        normalize: bool = False,
) -> pn.Column:
    tiers = set(df["maritime_tier"].dropna().unique())

    if selection in tiers:
        sub = df[df["maritime_tier"] == selection].copy()
        label = selection
    else:
        sub = df[df["country"] == selection].copy()
        label = selection

    if sub.empty:
        return pn.Column(f"No sectoral data for '{selection}'.")

    grouped = (
        sub.groupby("year")[["coal_co2", "oil_co2", "cement_co2", "gas_co2", "co2"]]
        .sum()
        .reset_index()
    )

    grouped = grouped[grouped["year"] >= 2000]
    if grouped.empty:
        return pn.Column(f"No sectoral data for '{selection}' from 2000 onwards.")

    grouped["other_co2"] = np.maximum(
        grouped["co2"]
        - (
                grouped["coal_co2"]
                + grouped["oil_co2"]
                + grouped["cement_co2"]
                + grouped["gas_co2"]
        ),
        0.0,
        )

    cols = ["coal_co2", "oil_co2", "cement_co2", "gas_co2", "other_co2"]

    if normalize:
        total = grouped[cols].sum(axis=1)
        for c in cols:
            grouped[c] = np.where(total > 0, grouped[c] / total * 100.0, 0.0)
        ylabel = "Share of total CO₂ (%)"
        title = f"Sectoral CO₂ shares – {label}"
    else:
        ylabel = "CO₂ (Mt)"
        title = f"Sectoral CO₂ levels – {label}"

    x_max = int(grouped["year"].max())

    area = grouped.hvplot.area(
        x="year",
        y=cols,
        stacked=True,
        alpha=0.9,
        legend="top_left",
        xlabel="Year",
        ylabel=ylabel,
        title=title,
        responsive=True,
        min_height=400,
    )

    area = area.redim.range(year=(2000, x_max)).opts(shared_axes=False)

    return pn.Column(pn.pane.HoloViews(area, sizing_mode="stretch_width"))


def create_sectoral_tab(df: pd.DataFrame) -> pn.Column:
    load_css("main_view.css")
    tier_options = sorted(df["maritime_tier"].dropna().unique())
    country_options = sorted(df["country"].dropna().unique())
    options: List[str] = tier_options + country_options

    if "Top 10 maritime (avg)" in options:
        default_selection = "Top 10 maritime (avg)"
    elif tier_options:
        default_selection = tier_options[0]
    else:
        default_selection = options[0] if options else None

    selection_widget = pn.widgets.Select(
        name="Group / country",
        options=options,
        value=default_selection,
        width=260,
    )

    normalize_toggle = pn.widgets.Checkbox(
        name="Show as % of total (normalized)",
        value=False,
    )

    sector_view = pn.bind(
        create_sectoral_breakdown,
        df=df,
        selection=selection_widget,
        normalize=normalize_toggle,
    )

    header = pn.pane.Markdown(
        "## Sectoral breakdown\n"
        "Which CO₂ sources dominate in different maritime tiers and countries?",
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )

    controls = pn.Row(
        selection_widget,
        normalize_toggle,
        sizing_mode="stretch_width",
    )

    content_card = pn.Column(
        controls,
        sector_view,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    return pn.Column(
        header,
        content_card,
        sizing_mode="stretch_width",
        css_classes=["story-layout"],
    )