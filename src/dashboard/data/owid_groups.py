# src/dashboard/data/owid_groups.py
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]   # .../DBG9
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


def _group_avg(df: pd.DataFrame, iso_list: List[str], col: str, label: str) -> pd.Series:
    tmp = df[df["iso_code"].isin(iso_list)]
    return tmp.groupby("year")[col].mean().rename(label)


def build_group_timeseries() -> Tuple[pd.DataFrame, List[str], List[str]]:
    owid = _load_owid()
    selected = owid[owid["iso_code"].isin(TOP10_ISO + BOTTOM10_ISO)].copy()

    co2_top = _group_avg(selected, TOP10_ISO, "co2", "co2_top10")
    co2_bottom = _group_avg(selected, BOTTOM10_ISO, "co2", "co2_bottom10")
    co2pc_top = _group_avg(selected, TOP10_ISO, "co2_per_capita", "co2pc_top10")
    co2pc_bottom = _group_avg(selected, BOTTOM10_ISO, "co2_per_capita", "co2pc_bottom10")
    co2gdp_top = _group_avg(selected, TOP10_ISO, "co2_per_gdp", "co2gdp_top10")
    co2gdp_bottom = _group_avg(selected, BOTTOM10_ISO, "co2_per_gdp", "co2gdp_bottom10")

    cement_top = _group_avg(selected, TOP10_ISO, "cement_co2", "cement_co2_top10")
    cement_bottom = _group_avg(selected, BOTTOM10_ISO, "cement_co2", "cement_co2_bottom10")
    coal_top = _group_avg(selected, TOP10_ISO, "coal_co2", "coal_co2_top10")
    coal_bottom = _group_avg(selected, BOTTOM10_ISO, "coal_co2", "coal_co2_bottom10")

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

    return df, TOP10_ISO, BOTTOM10_ISO


