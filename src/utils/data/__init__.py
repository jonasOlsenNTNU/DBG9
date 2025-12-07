"""
Data processing utilities for maritime emissions analysis.

This package contains expensive ETL operations that rebuild the analysis dataset.
Only run via: python -m src.dashboard.app --rebuild-dataset
"""
from __future__ import annotations
from .maritime_classifier import classify_maritime_intensity
from .data_pipeline import build_analysis_dataset, load_analysis_dataset

__all__ = [
    'classify_maritime_intensity',
    'build_analysis_dataset',
    'load_analysis_dataset',
]


from functools import lru_cache
from pathlib import Path

import pandas as pd

from .data_pipeline import build_analysis_dataset  # already exists


ROOT = Path(__file__).resolve().parents[3]  # .../DBG9
DATA_DIR = ROOT / "data"
ANALYSIS_PATH = DATA_DIR / "analysis_ready.csv"


@lru_cache(maxsize=1)
def load_analysis_dataset() -> pd.DataFrame:
    """
    Load the cached analysis-ready dataset produced by build_analysis_dataset().
    """
    if not ANALYSIS_PATH.exists():
        raise FileNotFoundError(
            f"{ANALYSIS_PATH} not found. Run `python -m src.dashboard.app --rebuild-dataset` first."
        )
    df = pd.read_csv(ANALYSIS_PATH)
    return df


def rebuild_analysis_dataset() -> pd.DataFrame:
    """
    Run the expensive ETL pipeline and refresh the cached CSV.
    """
    df = build_analysis_dataset()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(ANALYSIS_PATH, index=False)
    load_analysis_dataset.cache_clear()
    return df

