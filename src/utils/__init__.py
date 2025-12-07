"""
Utility modules for various dashboard operations.

Structure:
- data/ - Dataset building and processing (expensive operations)
- (future) visualization/ - Plot helpers
- (future) analysis/ - Statistical methods
"""

# Import data utilities for convenience
from .data import classify_maritime_intensity, build_analysis_dataset, load_analysis_dataset

__all__ = [
    'classify_maritime_intensity',
    'build_analysis_dataset',
    'load_analysis_dataset',
]
