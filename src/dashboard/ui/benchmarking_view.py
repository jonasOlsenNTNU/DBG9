# src/dashboard/ui/benchmarking_view.py
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import panel as pn


def find_peer_countries(
        df: pd.DataFrame,
        target_iso: str,
        gdp_tolerance: float = 0.2,
        port_tolerance: float = 0.5,
        same_region: bool = False,  # region not in dataset; placeholder
        min_peers: int = 5,
) -> pd.DataFrame:
    """
    Find peer countries similar in GDP per capita and port traffic volume.
    """
    latest_year = df["year"].max()
    base = df[df["year"] == latest_year].copy()

    if "gdp_per_capita" not in base.columns:
        base["gdp_per_capita"] = base["gdp"] / base["population"]

    target_row = base[base["iso_code"] == target_iso]
    if target_row.empty:
        return pd.DataFrame()

    target = target_row.iloc[0]
    gdp_pc = target["gdp_per_capita"]
    port = target["port_traffic"]

    peers = base[base["iso_code"] != target_iso].copy()
    peers["gdp_per_capita"] = peers["gdp_per_capita"].replace(0, np.nan)
    peers = peers.dropna(subset=["gdp_per_capita", "port_traffic"])

    peers = peers[
        (peers["gdp_per_capita"].between(gdp_pc * (1 - gdp_tolerance), gdp_pc * (1 + gdp_tolerance)))
        & (peers["port_traffic"].between(port * (1 - port_tolerance), port * (1 + port_tolerance)))
        ]

    if len(peers) < min_peers:
        # Expand tolerances a bit if too few peers
        peers = base[base["iso_code"] != target_iso].copy()
        peers["gdp_per_capita"] = peers["gdp_per_capita"].replace(0, np.nan)
        peers = peers.dropna(subset=["gdp_per_capita", "port_traffic"])
        peers = peers[
            (peers["gdp_per_capita"].between(gdp_pc * 0.5, gdp_pc * 1.5))
            & (peers["port_traffic"].between(port * 0.3, port * 1.7))
            ]

    # Similarity score (lower is better)
    peers["similarity"] = (
            np.abs(peers["gdp_per_capita"] - gdp_pc) / gdp_pc
            + np.abs(peers["port_traffic"] - port) / (port if port > 0 else 1)
    )

    return peers.sort_values("similarity")


def create_peer_comparison(
        df: pd.DataFrame,
        target_iso: str,
        peers: pd.DataFrame,
        year: int,
) -> pn.Column:
    """
    Table with key indicators and simple text "best practice" summary.
    """
    if peers.empty:
        return pn.Column("No suitable peers found.")

    base_year = df[df["year"] == year].copy()
    base = base_year[base_year["iso_code"] == target_iso]
    if base.empty:
        return pn.Column(f"No data for {target_iso} in {year}.")
    base_row = base.iloc[0]

    cols = [
        "country",
        "iso_code",
        "gdp_per_capita",
        "port_traffic",
        "co2_per_capita",
        "co2_per_teu",
        "decoupling_index",
    ]
    peers_year = base_year[base_year["iso_code"].isin(peers["iso_code"])].copy()
    if "gdp_per_capita" not in peers_year.columns:
        peers_year["gdp_per_capita"] = peers_year["gdp"] / peers_year["population"]

    table_df = peers_year[cols].copy()
    table_df["best_efficiency"] = table_df["co2_per_teu"] == table_df["co2_per_teu"].min()
    table_df.loc[table_df["best_efficiency"], "country"] = table_df["country"] + " ⭐"

    tab = pn.widgets.Tabulator(
        table_df.sort_values("co2_per_teu"),
        pagination="local",
        page_size=10,
        sizing_mode="stretch_both",
    )

    best = table_df.sort_values("co2_per_teu").iloc[0]
    delta_eff = base_row["co2_per_teu"] - best["co2_per_teu"]

    text = (
        "### Best practice summary\n\n"
        f"- Best-in-class peer: **{best['country']}**\n"
        f"- CO₂ per TEU difference vs target: **{delta_eff:.3f} kg/TEU**\n"
    )

    return pn.Column(tab, pn.pane.Markdown(text))


def create_benchmarking_tab(df: pd.DataFrame) -> pn.Column:
    """
    Full 'Peer Benchmarking' tab.
    Only countries with at least one peer are shown.
    """
    latest_year = df["year"].max()

    # Precompute which countries have peers
    all_countries = sorted(df["country"].unique())
    countries_with_peers: list[str] = []

    for country in all_countries:
        iso_codes = df.loc[df["country"] == country, "iso_code"].unique()
        if len(iso_codes) == 0:
            continue
        iso = iso_codes[0]
        peers = find_peer_countries(df, target_iso=iso)
        if not peers.empty:
            countries_with_peers.append(country)

    if not countries_with_peers:
        return pn.Column("No countries have suitable peers in this dataset.")

    default_country = "Norway" if "Norway" in countries_with_peers else countries_with_peers[0]

    country_select = pn.widgets.Select(
        name="Target country",
        options=countries_with_peers,
        value=default_country,
        width=250,
    )

    year_select = pn.widgets.IntSlider(
        name="Year",
        start=df["year"].min(),
        end=latest_year,
        value=latest_year,
    )

    @pn.depends(country_select.param.value, year_select.param.value)
    def _view(country, year):
        if not country:
            return pn.Column("Select a country.")
        iso_codes = df.loc[df["country"] == country, "iso_code"].unique()
        if len(iso_codes) == 0:
            return pn.Column(f"No ISO code for {country}.")
        iso = iso_codes[0]
        peers = find_peer_countries(df, target_iso=iso)
        if peers.empty:
            return pn.Column(f"No suitable peers found for {country}.")
        return create_peer_comparison(df, target_iso=iso, peers=peers, year=year)

    return pn.Column(
        pn.pane.Markdown("## Peer benchmarking\nCompare a country to similar peers."),
        pn.Row(country_select, year_select),
        _view,
        sizing_mode="stretch_both",
    )