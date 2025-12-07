"""
Data processing utilities for maritime emissions analysis.

This package contains expensive ETL operations that rebuild the analysis dataset.
Only run via: python -m src.dashboard.app --rebuild-dataset
"""

from .maritime_classifier import classify_maritime_intensity
from .data_pipeline import build_analysis_dataset, load_analysis_dataset

__all__ = [
    'classify_maritime_intensity',
    'build_analysis_dataset',
    'load_analysis_dataset',
]
