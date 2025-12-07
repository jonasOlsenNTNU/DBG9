# src/dashboard/ui/sectoral_view.py
from __future__ import annotations

import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas  # noqa: F401


def create_sectoral_breakdown(
        df: pd.DataFrame,
        maritime_tier: str,
        normalize: bool = False,
) -> pn.Column:
    """
    Stacked area chart of CO₂ by sector for a given maritime tier.
    X-axis is restricted to 2000+ (port+CO₂ era).
    """
    sub = df[df["maritime_tier"] == maritime_tier].copy()
    if sub.empty:
        return pn.Column(f"No data for tier '{maritime_tier}'.")

    grouped = (
        sub.groupby("year")[["coal_co2", "oil_co2", "cement_co2", "gas_co2", "co2"]]
        .sum()
        .reset_index()
        .sort_values("year")
    )

    grouped = grouped[grouped["year"] >= 2000]
    if grouped.empty:
        return pn.Column(f"No sectoral data for '{maritime_tier}' from 2000 onwards.")

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
        title = f"Sectoral CO₂ shares – {maritime_tier}"
    else:
        ylabel = "CO₂ (Mt)"
        title = f"Sectoral CO₂ levels – {maritime_tier}"

    x_max = int(grouped["year"].max())

    area = grouped.hvplot.area(
        x="year",
        y=cols,
        stacked=True,
        ylabel=ylabel,
        xlabel="Year",
        title=title,
        height=400,
        responsive=False,
    )

    # Break global axis linking and clamp to 2000..x_max
    area = area.redim.range(year=(2000, x_max)).opts(shared_axes=False)

    return pn.Column(pn.pane.HoloViews(area, sizing_mode="stretch_both"))


def create_maritime_share_plot(df: pd.DataFrame) -> pn.Column:
    """
    Scatter: X = port traffic, Y = maritime CO₂ share (% of total CO₂).
    Uses the latest year where maritime_share is available (no slider).
    """
    if "maritime_share" not in df.columns or "maritime_co2" not in df.columns:
        return pn.Column("OECD maritime data not available in this dataset.")

    # Find the latest year with valid maritime_share data
    mask = df["maritime_share"].notna()
    if not mask.any():
        return pn.Column("No OECD maritime CO₂ data in this dataset.")

    latest_year = int(df.loc[mask, "year"].max())
    sub = df[(df["year"] == latest_year) & df["maritime_share"].notna()]

    if sub.empty:
        return pn.Column(f"No OECD maritime CO₂ data for {latest_year}.")

    scatter = sub.hvplot.scatter(
        x="port_traffic",
        y="maritime_share",
        hover_cols=["country", "maritime_co2", "co2"],
        xlabel="Port traffic (TEU)",
        ylabel="Maritime CO₂ share of total (%)",
        title=f"Maritime CO₂ share vs port activity – {latest_year}",
        responsive=True,
        min_height=400,
    )

    return pn.Column(
        pn.pane.Markdown(
            "## Maritime CO₂ share (OECD)\n"
            f"How much of national CO₂ comes from maritime transport in {latest_year}?"
        ),
        pn.pane.HoloViews(scatter, sizing_mode="stretch_both"),
        sizing_mode="stretch_both",
    )


def create_sectoral_tab(df: pd.DataFrame) -> pn.Column:
    """
    Full 'Sectoral Breakdown' tab: tier selector + normalized toggle + OECD maritime scatter.
    Uses pn.bind instead of a depends-decorated function to avoid any weird recursion.
    """
    tier_options = sorted(df["maritime_tier"].dropna().unique())
    default_tier = tier_options[0] if tier_options else None

    tier_select = pn.widgets.Select(
        name="Maritime tier",
        options=tier_options,
        value=default_tier,
        width=200,
    )

    normalize_toggle = pn.widgets.Checkbox(
        name="Show as % of total (normalized)",
        value=False,
    )

    # This binding returns a *new* Column whenever the widgets change
    sector_view = pn.bind(
        lambda tier, norm: create_sectoral_breakdown(
            df, maritime_tier=tier, normalize=norm
        )
        if tier is not None
        else pn.Column("No tier selected."),
        tier_select,
        normalize_toggle,
    )

    maritime_share_section = create_maritime_share_plot(df)

    return pn.Column(
        pn.pane.Markdown(
            "## Sectoral breakdown\n"
            "Which CO₂ sources dominate in different maritime tiers?"
        ),
        pn.Row(tier_select, normalize_toggle),
        sector_view,
        maritime_share_section,
        sizing_mode="stretch_both",
    )
