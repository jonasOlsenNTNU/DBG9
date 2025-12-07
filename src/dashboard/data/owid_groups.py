from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
OWID_PATH = DATA_DIR / "owid-co2-data.csv"

TOP10_ISO: List[str] = [
    "CHN",  # China
    "USA",  # United States
    "SGP",  # Singapore
    "NLD",  # Netherlands
    "GRC",  # Greece
    "JPN",  # Japan
    "KOR",  # South Korea
    "DEU",  # Germany
    "GBR",  # United Kingdom
    "ARE",  # United Arab Emirates
]

BOTTOM10_ISO: List[str] = [
    "ISL",  # Iceland
    "EST",  # Estonia
    "LVA",  # Latvia
    "LTU",  # Lithuania
    "CYP",  # Cyprus
    "MAR",  # Morocco
    "TUN",  # Tunisia
    "ALB",  # Albania
    "TGO",  # Togo
    "BEN",  # Benin
]


def _load_owid() -> pd.DataFrame:
    df = pd.read_csv(OWID_PATH)
    df = df[df["iso_code"].str.len() == 3]
    return df[
        [
            "iso_code",
            "country",
            "year",
            "co2",
            "co2_per_capita",
            "co2_per_gdp",
            "cement_co2",
            "coal_co2",
        ]
    ]
PORT_PATH = DATA_DIR / "port_traffic_data.csv"
COUNTRY_COL = "Country Name"
CODE_COL = "Country Code"



def _group_avg(df: pd.DataFrame, iso_list: List[str], col: str, label: str) -> pd.Series:
    tmp = df[df["iso_code"].isin(iso_list)]
    return tmp.groupby("year")[col].mean().rename(label)
def _load_port_long() -> pd.DataFrame:
    df_raw = pd.read_csv(PORT_PATH, skiprows=4)
    year_cols = [c for c in df_raw.columns if str(c).isdigit()]

    df_long = df_raw.melt(
        id_vars=[COUNTRY_COL, CODE_COL],
        value_vars=year_cols,
        var_name="year",
        value_name="port_traffic",
    )

    df_long["year"] = df_long["year"].astype(int)
    df_long = df_long.dropna(subset=["port_traffic"])
    df_long = df_long[df_long["port_traffic"] > 0]
    df_long = df_long.rename(columns={CODE_COL: "iso_code"})
    return df_long


def _compute_dynamic_groups(owid: pd.DataFrame) -> Tuple[List[str], List[str]]:
    try:
        df_port = _load_port_long()
    except FileNotFoundError:
        print("Warning: port_traffic_data.csv not found; using static Top/Bottom-10 groups.")
        return TOP10_ISO, BOTTOM10_ISO

    valid_iso = set(owid["iso_code"].unique())
    df_port = df_port[df_port["iso_code"].isin(valid_iso)]

    df_port = df_port[df_port["year"] >= 2000]

    if df_port.empty or df_port["iso_code"].nunique() < 20:
        print("Warning: Not enough port-traffic data to recompute groups; using static Top/Bottom-10.")
        return TOP10_ISO, BOTTOM10_ISO

    agg = (
        df_port.groupby("iso_code", as_index=False)["port_traffic"]
        .mean()
        .sort_values("port_traffic", ascending=False)
    )

    dynamic_top = agg.head(10)["iso_code"].tolist()

    remaining = agg[~agg["iso_code"].isin(dynamic_top)].sort_values(
        "port_traffic", ascending=True
    )
    dynamic_bottom = remaining.head(10)["iso_code"].tolist()

    return dynamic_top, dynamic_bottom



def build_group_timeseries() -> Tuple[pd.DataFrame, List[str], List[str]]:
    owid = _load_owid()

    top_iso, bottom_iso = _compute_dynamic_groups(owid)

    selected = owid[owid["iso_code"].isin(top_iso + bottom_iso)].copy()

    co2_top = _group_avg(selected, top_iso, "co2", "co2_top10")
    co2_bottom = _group_avg(selected, bottom_iso, "co2", "co2_bottom10")
    co2pc_top = _group_avg(selected, top_iso, "co2_per_capita", "co2pc_top10")
    co2pc_bottom = _group_avg(selected, bottom_iso, "co2_per_capita", "co2pc_bottom10")
    co2gdp_top = _group_avg(selected, top_iso, "co2_per_gdp", "co2gdp_top10")
    co2gdp_bottom = _group_avg(selected, bottom_iso, "co2_per_gdp", "co2gdp_bottom10")

    cement_top = _group_avg(selected, top_iso, "cement_co2", "cement_co2_top10")
    cement_bottom = _group_avg(selected, bottom_iso, "cement_co2", "cement_co2_bottom10")
    coal_top = _group_avg(selected, top_iso, "coal_co2", "coal_co2_top10")
    coal_bottom = _group_avg(selected, bottom_iso, "coal_co2", "coal_co2_bottom10")

    df = (
        pd.concat(
            [
                co2_top,
                co2_bottom,
                co2pc_top,
                co2pc_bottom,
                co2gdp_top,
                co2gdp_bottom,
                cement_top,
                cement_bottom,
                coal_top,
                coal_bottom,
            ],
            axis=1,
        )
        .reset_index()
        .sort_values("year")
    )

    df["co2_ratio_top_over_bottom"] = df["co2_top10"] / df["co2_bottom10"]
    base_top = df["co2_top10"].iloc[0]
    base_bottom = df["co2_bottom10"].iloc[0]
    df["co2_top10_index"] = df["co2_top10"] / base_top
    df["co2_bottom10_index"] = df["co2_bottom10"] / base_bottom

    return df, top_iso, bottom_iso