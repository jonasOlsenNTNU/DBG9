"""
Maritime intensity classification system.

Classifies countries into maritime tiers based on port traffic intensity,
data quality, and multiple metrics (per capita, per GDP, absolute volume).

Addresses Issue #1 from feature plan: Dynamic classification to avoid
misclassifying mid-tier countries (Morocco, Tunisia, etc.) as "low maritime".
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

MaritimeTier = Literal["china", "high", "medium-high", "medium-low", "low"]
DataQuality = Literal["complete", "interpolated", "sparse"]


def classify_maritime_intensity(
    df_port: pd.DataFrame,
    df_owid: pd.DataFrame,
    year: int = 2022,
    min_years_coverage: int = 15,
    max_gap_years: int = 3
) -> pd.DataFrame:
    """
    Classify countries by maritime intensity using multiple metrics.
    
    Args:
        df_port: Port traffic data (long format with columns: Country Code, year, port_traffic)
        df_owid: OWID data with population, gdp, iso_code
        year: Reference year for classification (default: 2022, latest port data)
        min_years_coverage: Minimum number of non-missing years required (default: 15)
        max_gap_years: Maximum consecutive missing years allowed (default: 3)
    
    Returns:
        DataFrame with columns:
        - iso_code: 3-letter country code
        - country_name: Country name
        - maritime_tier: 'china' | 'high' | 'medium-high' | 'medium-low' | 'low'
        - teu_per_capita: Port traffic per capita (latest year)
        - teu_per_gdp: Port traffic per million USD GDP (latest year)
        - total_teu: Absolute port traffic (latest year)
        - data_quality: 'complete' | 'interpolated' | 'sparse'
        - years_available: Number of non-missing years (2000-2022)
        - max_gap_years: Maximum consecutive year gap
    
    Classification logic:
        - China: Analyzed separately due to dominance (56% port, 59% CO2)
        - High: Top 25% TEU/capita AND top 33% absolute volume
        - Medium-high: Top 25% TEU/capita OR top 33% absolute volume
        - Low: Bottom 25% TEU/capita AND bottom 33% absolute volume
        - Medium-low: Everything else
    
    Example:
        >>> df_class = classify_maritime_intensity(df_port, df_owid, year=2022)
        >>> df_class[df_class['maritime_tier'] == 'high']['country_name'].tolist()
        ['Singapore', 'Netherlands', 'Belgium', 'United Arab Emirates', ...]
    """
    
    # Merge port data with OWID for population/GDP
    df_merged = df_port.merge(
        df_owid[['iso_code', 'year', 'population', 'gdp', 'country']],
        left_on=['Country Code', 'year'],
        right_on=['iso_code', 'year'],
        how='inner'
    )
    
    # Calculate data quality metrics per country
    quality_metrics = _calculate_data_quality(df_merged, min_years_coverage, max_gap_years)
    
    # Filter to valid countries (meet quality thresholds)
    valid_countries = quality_metrics[
        quality_metrics['data_quality'] != 'sparse'
    ]['iso_code'].unique()
    
    df_valid = df_merged[df_merged['iso_code'].isin(valid_countries)]
    
    # Get latest year data for classification
    df_latest = df_valid[df_valid['year'] == year].copy()
    
    if df_latest.empty:
        # Fallback to most recent year if specified year not available
        latest_available = df_valid['year'].max()
        print(f"Warning: Year {year} not available, using {latest_available}")
        df_latest = df_valid[df_valid['year'] == latest_available].copy()
    
    # Calculate intensity metrics
    df_latest['teu_per_capita'] = df_latest['port_traffic'] / df_latest['population']
    df_latest['teu_per_gdp'] = df_latest['port_traffic'] / (df_latest['gdp'] / 1e6)  # TEU per $1M GDP
    df_latest['total_teu'] = df_latest['port_traffic']
    
    # Drop rows with missing metrics
    df_latest = df_latest.dropna(subset=['teu_per_capita', 'teu_per_gdp', 'total_teu'])
    
    # Calculate percentile thresholds
    teu_pc_q75 = df_latest['teu_per_capita'].quantile(0.75)
    teu_pc_q25 = df_latest['teu_per_capita'].quantile(0.25)
    total_q67 = df_latest['total_teu'].quantile(0.67)
    total_q33 = df_latest['total_teu'].quantile(0.33)
    
    # Classify into tiers
    def assign_tier(row) -> MaritimeTier:
        if row['iso_code'] == 'CHN':
            return 'china'
        elif (row['teu_per_capita'] >= teu_pc_q75) and (row['total_teu'] >= total_q67):
            return 'high'
        elif (row['teu_per_capita'] >= teu_pc_q75) or (row['total_teu'] >= total_q67):
            return 'medium-high'
        elif (row['teu_per_capita'] <= teu_pc_q25) and (row['total_teu'] <= total_q33):
            return 'low'
        else:
            return 'medium-low'
    
    df_latest['maritime_tier'] = df_latest.apply(assign_tier, axis=1)
    
    # Merge with quality metrics
    result = df_latest[['iso_code', 'country', 'maritime_tier', 
                        'teu_per_capita', 'teu_per_gdp', 'total_teu']].merge(
        quality_metrics[['iso_code', 'data_quality', 'years_available', 'max_gap_years']],
        on='iso_code',
        how='left'
    )
    
    result = result.rename(columns={'country': 'country_name'})
    
    return result.sort_values('teu_per_capita', ascending=False).reset_index(drop=True)


def _calculate_data_quality(
    df: pd.DataFrame,
    min_years: int,
    max_gap: int
) -> pd.DataFrame:
    """
    Calculate data quality metrics for each country.
    
    Args:
        df: Merged dataframe with iso_code, year, port_traffic
        min_years: Minimum years required for 'complete'/'interpolated' status
        max_gap: Maximum consecutive missing years allowed
    
    Returns:
        DataFrame with iso_code, data_quality, years_available, max_gap_years
    """
    quality_records = []
    
    for iso_code in df['iso_code'].unique():
        country_data = df[df['iso_code'] == iso_code].sort_values('year')
        
        # Count available years
        years_available = country_data['year'].nunique()
        
        # Calculate max consecutive gap
        years = sorted(country_data['year'].unique())
        gaps = [years[i+1] - years[i] - 1 for i in range(len(years) - 1)]
        max_gap_years = max(gaps) if gaps else 0
        
        # Determine quality
        if years_available < min_years or max_gap_years > max_gap:
            quality = 'sparse'
        elif max_gap_years == 0:
            quality = 'complete'
        else:
            quality = 'interpolated'
        
        quality_records.append({
            'iso_code': iso_code,
            'data_quality': quality,
            'years_available': years_available,
            'max_gap_years': max_gap_years
        })
    
    return pd.DataFrame(quality_records)


def load_and_classify(
    year: int = 2022,
    min_years_coverage: int = 15,
    max_gap_years: int = 3
) -> pd.DataFrame:
    """
    Convenience function to load data and classify in one call.
    
    Args:
        year: Reference year for classification
        min_years_coverage: Minimum years required
        max_gap_years: Maximum consecutive gap allowed
    
    Returns:
        Classification DataFrame
    """
    from .data_pipeline import load_port_long, load_owid_base
    
    df_port = load_port_long()
    df_owid = load_owid_base()
    
    return classify_maritime_intensity(
        df_port, df_owid, year, min_years_coverage, max_gap_years
    )


if __name__ == '__main__':
    # Test classification
    print("Running maritime classification...")
    df_class = load_and_classify()
    
    print(f"\nTotal countries classified: {len(df_class)}")
    print("\nDistribution by tier:")
    print(df_class['maritime_tier'].value_counts())
    
    print("\nData quality distribution:")
    print(df_class['data_quality'].value_counts())
    
    print("\nTop 10 by TEU per capita:")
    print(df_class[['country_name', 'maritime_tier', 'teu_per_capita', 'total_teu']].head(10))
    
    print("\nChina:")
    print(df_class[df_class['iso_code'] == 'CHN'][['country_name', 'maritime_tier', 'teu_per_capita', 'total_teu']])
    
    print("\nHigh maritime economies:")
    high_maritime = df_class[df_class['maritime_tier'] == 'high']
    print(high_maritime[['country_name', 'teu_per_capita', 'total_teu']])
