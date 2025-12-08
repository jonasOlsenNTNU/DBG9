from __future__ import annotations
from typing import List
import numpy as np
import pandas as pd
import panel as pn
from ..utils.load_css import load_css


def find_peer_countries(
        df: pd.DataFrame,
        target_iso: str,
        gdp_tolerance: float = 0.2,
        port_tolerance: float = 0.5,
        same_region: bool = False,
        min_peers: int = 5,
) -> pd.DataFrame:
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
        peers = base[base["iso_code"] != target_iso].copy()
        peers["gdp_per_capita"] = peers["gdp_per_capita"].replace(0, np.nan)
        peers = peers.dropna(subset=["gdp_per_capita", "port_traffic"])
        peers = peers[
            (peers["gdp_per_capita"].between(gdp_pc * 0.5, gdp_pc * 1.5))
            & (peers["port_traffic"].between(port * 0.3, port * 1.7))
            ]

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
    base_year = df[df["year"] == year].copy()
    base = base_year[base_year["iso_code"] == target_iso]
    if base.empty:
        return pn.Column(f"No data for {target_iso} in {year}.")
    base_row = base.iloc[0]

    if "gdp_per_capita" in base_row.index:
        base_gdp_pc = base_row["gdp_per_capita"]
    else:
        if ("gdp" in base_row.index) and ("population" in base_row.index) and base_row["population"] > 0:
            base_gdp_pc = base_row["gdp"] / base_row["population"]
        else:
            base_gdp_pc = np.nan

    peers_year = base_year[base_year["iso_code"].isin(peers["iso_code"])].copy()
    if "gdp_per_capita" not in peers_year.columns:
        if {"gdp", "population"}.issubset(peers_year.columns):
            peers_year["gdp_per_capita"] = np.where(
                peers_year["population"] > 0,
                peers_year["gdp"] / peers_year["population"],
                np.nan,
                )
        else:
            peers_year["gdp_per_capita"] = np.nan

    cols = [
        "country",
        "iso_code",
        "gdp_per_capita",
        "port_traffic",
        "co2_per_capita",
        "co2_per_teu",
        "decoupling_index",
    ]
    cols = [c for c in cols if c in peers_year.columns]

    table_df = peers_year[cols].copy()
    table_df["best_efficiency"] = table_df["co2_per_teu"] == table_df["co2_per_teu"].min()
    table_df.loc[table_df["best_efficiency"], "country"] = (
            table_df["country"].astype(str) + " ⭐"
    )
    table_df = table_df.reset_index(drop=True)

    tab = pn.widgets.Tabulator(
        table_df.sort_values("co2_per_teu"),
        pagination="local",
        page_size=10,
        height=320,
        sizing_mode="stretch_width",
        show_index=False,          # <— important
    )
    best = table_df.sort_values("co2_per_teu").iloc[0]
    delta_eff = base_row["co2_per_teu"] - best["co2_per_teu"]

    target_text = (
        f"### Target country snapshot – {base_row['country']} ({year})\n\n"
        f"- GDP per capita: **{base_gdp_pc:,.0f}**\n"
        f"- Port traffic: **{base_row['port_traffic']:,.0f} TEU**\n"
        f"- CO₂ per capita: **{base_row['co2_per_capita']:.2f} t/person**\n"
        f"- CO₂ per TEU: **{base_row['co2_per_teu']:.3f} kg/TEU**\n"
        f"- Decoupling index: **{base_row['decoupling_index']:.2f}** "
        "(higher = stronger decoupling)\n"
    )

    text = (
        "### Best practice summary\n\n"
        f"- Best-in-class peer: **{best['country']}**\n"
        f"- CO₂ per TEU difference vs target: **{delta_eff:.3f} kg/TEU**\n"
        "  (negative value means the peer is more efficient)\n"
    )

    return pn.Column(
        pn.Row(
            pn.pane.Markdown(target_text, sizing_mode="stretch_width"),
        ),
        tab,
        pn.pane.Markdown(text, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )


def create_benchmarking_tab(df: pd.DataFrame) -> pn.Column:
    load_css("main_view.css")
    latest_year = df["year"].max()

    all_countries = sorted(df["country"].unique())
    countries_with_peers: List[str] = []
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

    intro = pn.pane.Markdown(
        """
## Peer benchmarking – how are countries doing relative to similar peers?

We pick **peer countries** in the selected year with similar **GDP per capita**
and **port traffic**:

- First pass: ±20% in GDP per capita and ±50% in port traffic.  
- If this yields too few peers, we automatically widen to a broader window
  (about 50–150% of GDP per capita and 30–170% of port traffic).

Use the table to compare **CO₂ per TEU**, CO₂ per capita, GDP per capita and port traffic.  
The ⭐ marks the most CO₂-efficient peer (lowest CO₂ per TEU), and the summary
shows how far the chosen country is from this best practice.
        """,
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )


    controls = pn.Row(
        country_select,
        year_select,
        sizing_mode="stretch_width",
    )

    content_card = pn.Column(
        controls,
        _view,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    return pn.Column(
        intro,
        content_card,
        sizing_mode="stretch_width",
        css_classes=["story-layout"],
    )