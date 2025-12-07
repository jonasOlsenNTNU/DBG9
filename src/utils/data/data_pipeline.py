"""
Data pipeline for building analysis-ready dataset.

This module handles expensive ETL operations:
- Loading raw data (port traffic, OWID CO2, OECD maritime)
- Merging datasets
- Calculating derived metrics (CO2/TEU, decoupling index, etc.)
- Interpolating missing values
- Saving to cached CSV

WARNING: This is expensive (~30-60 seconds). Only run via:
    python -m src.dashboard.app --rebuild-dataset
or directly:
    python src/utils/build_dataset.py

Normal dashboard operation loads from cached data/analysis_ready.csv
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
PORT_PATH = DATA_DIR / "port_traffic_data.csv"
OWID_PATH = DATA_DIR / "owid-co2-data.csv"
OECD_PATH = DATA_DIR / "oecd.csv"
OUTPUT_PATH = DATA_DIR / "analysis_ready.csv"

COUNTRY_COL = "Country Name"
CODE_COL = "Country Code"


def load_port_long() -> pd.DataFrame:
    """
    Load WDI port traffic data in long format.
    
    Returns:
        DataFrame with columns: Country Name, Country Code, year, port_traffic
    """
    df_raw = pd.read_csv(PORT_PATH, skiprows=4)
    year_cols = [c for c in df_raw.columns if c.isdigit()]
    
    df_long = df_raw.melt(
        id_vars=[COUNTRY_COL, CODE_COL],
        value_vars=year_cols,
        var_name="year",
        value_name="port_traffic",
    )
    
    df_long["year"] = df_long["year"].astype(int)
    df_long = df_long.dropna(subset=["port_traffic"])
    df_long = df_long[df_long["port_traffic"] > 0]
    
    return df_long


def load_owid_base() -> pd.DataFrame:
    """
    Load base OWID data (all columns for classification and analysis).
    
    Returns:
        DataFrame with iso_code, year, country, co2, population, gdp, energy, etc.
    """
    df = pd.read_csv(OWID_PATH)
    
    # Filter to 3-letter ISO codes (exclude aggregates like "World", "OECD")
    df = df[df["iso_code"].str.len() == 3]
    
    # Convert year to int
    df["year"] = df["year"].astype(int)
    
    return df


def load_oecd_maritime() -> Optional[pd.DataFrame]:
    """
    Load OECD maritime transport CO2 data (monthly → aggregate to annual).
    
    Returns:
        DataFrame with iso_code, year, maritime_co2 (tonnes)
        Returns None if file doesn't exist or can't be parsed
    """
    if not OECD_PATH.exists():
        print(f"Warning: OECD file not found at {OECD_PATH}")
        return None
    
    try:
        # OECD format: Complex header structure, skip to data rows
        df = pd.read_csv(OECD_PATH, low_memory=False)
        
        # Check if required columns exist
        required = ['REF_AREA', 'TIME_PERIOD', 'OBS_VALUE', 'POLLUTANT']
        if not all(col in df.columns for col in required):
            print("Warning: OECD file missing required columns")
            return None
        
        # Filter to CO2 only
        df = df[df['POLLUTANT'] == 'CO2']
        
        # Parse time period (format: YYYY-MM)
        df['year'] = pd.to_datetime(df['TIME_PERIOD'], errors='coerce').dt.year
        df = df.dropna(subset=['year'])
        df['year'] = df['year'].astype(int)
        
        # Aggregate monthly to annual
        maritime_annual = df.groupby(['REF_AREA', 'year'], as_index=False)['OBS_VALUE'].sum()
        maritime_annual.columns = ['iso_code', 'year', 'maritime_co2']
        
        return maritime_annual
    
    except Exception as e:
        print(f"Warning: Failed to load OECD data: {e}")
        return None


def interpolate_gaps(df: pd.DataFrame, column: str, max_gap: int = 2) -> pd.DataFrame:
    """
    Interpolate missing values within each country's time series.
    
    Args:
        df: DataFrame with iso_code (or Country Code), year, column
        column: Column name to interpolate
        max_gap: Maximum gap size to fill (default: 2 years)
    
    Returns:
        DataFrame with interpolated values and has_interpolated_{column} flag
    """
    df = df.copy()
    
    # Identify grouping column
    group_col = 'iso_code' if 'iso_code' in df.columns else CODE_COL
    
    # Store original nulls
    original_nulls = df[column].isna()
    
    # Interpolate within each country
    df[column] = df.groupby(group_col)[column].transform(
        lambda x: x.interpolate(method='linear', limit=max_gap, limit_area='inside')
    )
    
    # Flag interpolated values
    df[f'has_interpolated_{column}'] = original_nulls & df[column].notna()
    
    return df


def calculate_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate derived metrics from raw data.
    
    Args:
        df: Merged DataFrame with port_traffic, co2, population, gdp, etc.
    
    Returns:
        DataFrame with additional columns:
        - co2_per_teu: kg CO2 per TEU
        - port_cagr_7y: 7-year compound annual growth rate (port)
        - co2_cagr_7y: 7-year CAGR (CO2)
        - decoupling_index: port_cagr_7y - co2_cagr_7y
        - oil_share: oil_co2 / co2
        - coal_share: coal_co2 / co2
        - cement_share: cement_co2 / co2
        - renewable_share: (if available in OWID)
    """
    df = df.copy()
    
    # CO2 per TEU (kg CO2 per TEU)
    df['co2_per_teu'] = (df['co2'] * 1e6) / df['port_traffic']  # co2 in Mt, convert to kg
    
    # 7-year growth rates (CAGR)
    def calculate_cagr(series, periods=7):
        """Calculate compound annual growth rate."""
        shifted = series.shift(periods)
        cagr = ((series / shifted) ** (1 / periods)) - 1
        return cagr
    
    df = df.sort_values(['iso_code', 'year'])
    
    df['port_cagr_7y'] = df.groupby('iso_code')['port_traffic'].transform(
        lambda x: calculate_cagr(x, periods=7)
    )
    
    df['co2_cagr_7y'] = df.groupby('iso_code')['co2'].transform(
        lambda x: calculate_cagr(x, periods=7)
    )
    
    # Decoupling index (positive = port growing faster than CO2)
    df['decoupling_index'] = df['port_cagr_7y'] - df['co2_cagr_7y']
    
    # Sectoral shares (handle missing data)
    for sector in ['oil', 'coal', 'cement', 'gas']:
        col = f'{sector}_co2'
        if col in df.columns:
            df[f'{sector}_share'] = df[col] / df['co2'].replace(0, np.nan) * 100
            df[f'{sector}_share'] = df[f'{sector}_share'].fillna(0)
    
    # Energy metrics (if available)
    if 'renewables_energy_per_capita' in df.columns or 'renewables_share_energy' in df.columns:
        # OWID has multiple renewable columns, use share if available
        if 'renewables_share_energy' in df.columns:
            df['renewable_share'] = df['renewables_share_energy']
    
    return df


def build_analysis_dataset(
    interpolate: bool = True,
    max_gap: int = 2,
    year_range: tuple[int, int] = (2000, 2024)
) -> pd.DataFrame:
    """
    Build complete analysis-ready dataset from all sources.
    
    This is the main ETL pipeline. Expensive operation (~30-60 seconds).
    
    Args:
        interpolate: Whether to interpolate small gaps (default: True)
        max_gap: Maximum gap size to interpolate (default: 2 years)
        year_range: (start_year, end_year) to include (default: 2000-2024)
    
    Returns:
        Complete analysis DataFrame with:
        - Country identifiers (iso_code, country_name)
        - Time (year)
        - Port metrics (port_traffic, teu_per_capita, teu_per_gdp)
        - CO2 metrics (co2, co2_per_capita, co2_per_gdp, co2_per_teu, sectoral breakdown)
        - Derived metrics (CAGR, decoupling_index, sectoral shares)
        - Maritime classification (maritime_tier, data_quality)
        - Data quality flags (has_interpolated_*)
    
    Example:
        >>> df = build_analysis_dataset()
        >>> df.to_csv('data/analysis_ready.csv', index=False)
    """
    print("=" * 60)
    print("Building analysis dataset...")
    print("=" * 60)
    
    # Step 1: Load raw data
    print("\n[1/6] Loading raw data...")
    df_port = load_port_long()
    print(f"  ✓ Port traffic: {len(df_port)} rows, {df_port['Country Code'].nunique()} countries")
    
    df_owid = load_owid_base()
    print(f"  ✓ OWID CO2: {len(df_owid)} rows, {df_owid['iso_code'].nunique()} countries")
    
    df_oecd = load_oecd_maritime()
    if df_oecd is not None:
        print(f"  ✓ OECD maritime: {len(df_oecd)} rows, {df_oecd['iso_code'].nunique()} countries")
    else:
        print("  ⚠ OECD maritime: Not available")
    
    # Step 2: Filter year range
    print(f"\n[2/6] Filtering to {year_range[0]}-{year_range[1]}...")
    df_port = df_port[(df_port['year'] >= year_range[0]) & (df_port['year'] <= year_range[1])]
    df_owid = df_owid[(df_owid['year'] >= year_range[0]) & (df_owid['year'] <= year_range[1])]
    if df_oecd is not None:
        df_oecd = df_oecd[(df_oecd['year'] >= year_range[0]) & (df_oecd['year'] <= year_range[1])]
    
    # Step 3: Merge port + OWID
    print("\n[3/6] Merging datasets...")
    df_merged = df_port.merge(
        df_owid,
        left_on=[CODE_COL, 'year'],
        right_on=['iso_code', 'year'],
        how='inner'
    )
    print(f"  ✓ Port + OWID: {len(df_merged)} rows, {df_merged['iso_code'].nunique()} countries")
    
    # Add OECD maritime if available
    if df_oecd is not None:
        df_merged = df_merged.merge(
            df_oecd,
            on=['iso_code', 'year'],
            how='left'
        )
        # Calculate maritime share
        df_merged['maritime_share'] = df_merged['maritime_co2'] / (df_merged['co2'] * 1e6) * 100  # OWID CO2 in Mt, OECD in tonnes
        print(f"  ✓ Added OECD maritime data for {df_merged['maritime_co2'].notna().sum()} country-years")
    
    # Step 4: Interpolate missing values
    if interpolate:
        print(f"\n[4/6] Interpolating gaps (max {max_gap} years)...")
        df_merged = interpolate_gaps(df_merged, 'port_traffic', max_gap)
        interpolated_count = df_merged['has_interpolated_port_traffic'].sum()
        print(f"  ✓ Interpolated {interpolated_count} port traffic values")
    else:
        print("\n[4/6] Skipping interpolation")
        df_merged['has_interpolated_port_traffic'] = False
    
    # Step 5: Calculate derived metrics
    print("\n[5/6] Calculating derived metrics...")
    df_merged = calculate_derived_metrics(df_merged)
    print("  ✓ Added: co2_per_teu, port_cagr_7y, co2_cagr_7y, decoupling_index")
    print("  ✓ Added: oil_share, coal_share, cement_share, gas_share")
    
    # Step 6: Add maritime classification
    print("\n[6/6] Classifying maritime intensity...")
    from .maritime_classifier import classify_maritime_intensity
    
    df_class = classify_maritime_intensity(df_port, df_owid, year=2022)
    print(f"  ✓ Classified {len(df_class)} countries")
    print(f"    Maritime tiers: {df_class['maritime_tier'].value_counts().to_dict()}")
    
    # Merge classification
    df_merged = df_merged.merge(
        df_class[['iso_code', 'maritime_tier', 'data_quality']],
        on='iso_code',
        how='left'
    )
    
    # Step 7: Select and order final columns
    print("\nFinalizing dataset...")
    
    # Core columns (always include)
    core_cols = [
        'iso_code', 'country', 'year',
        'maritime_tier', 'data_quality',
        'port_traffic', 'co2', 'population', 'gdp'
    ]
    
    # Intensity metrics
    intensity_cols = [
        'co2_per_capita', 'co2_per_gdp', 'co2_per_teu',
        'energy_per_capita', 'energy_per_gdp'
    ]
    
    # Sectoral breakdown
    sectoral_cols = [
        'coal_co2', 'oil_co2', 'cement_co2', 'gas_co2',
        'coal_share', 'oil_share', 'cement_share', 'gas_share'
    ]
    
    # Derived metrics
    derived_cols = [
        'port_cagr_7y', 'co2_cagr_7y', 'decoupling_index',
        'maritime_co2', 'maritime_share'
    ]
    
    # Flags
    flag_cols = ['has_interpolated_port_traffic']
    
    # Combine all columns that exist
    final_cols = []
    for col_list in [core_cols, intensity_cols, sectoral_cols, derived_cols, flag_cols]:
        for col in col_list:
            if col in df_merged.columns and col not in final_cols:
                final_cols.append(col)
    
    df_final = df_merged[final_cols].copy()
    
    # Sort by country and year
    df_final = df_final.sort_values(['iso_code', 'year']).reset_index(drop=True)
    
    # Summary
    print("\n" + "=" * 60)
    print("Dataset build complete!")
    print("=" * 60)
    print(f"  Rows: {len(df_final):,}")
    print(f"  Countries: {df_final['iso_code'].nunique()}")
    print(f"  Years: {df_final['year'].min()}-{df_final['year'].max()}")
    print(f"  Columns: {len(df_final.columns)}")
    print(f"  Interpolated values: {df_final['has_interpolated_port_traffic'].sum()}")
    print(f"\n  Maritime tier distribution:")
    for tier, count in df_final.groupby('maritime_tier')['iso_code'].nunique().items():
        print(f"    {tier}: {count} countries")
    
    return df_final


def save_analysis_dataset(df: pd.DataFrame, output_path: Path = OUTPUT_PATH) -> None:
    """
    Save analysis dataset to CSV.
    
    Args:
        df: Analysis DataFrame
        output_path: Where to save (default: data/analysis_ready.csv)
    """
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def load_analysis_dataset(input_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    """
    Load cached analysis dataset from CSV.
    
    Args:
        input_path: Where to load from (default: data/analysis_ready.csv)
    
    Returns:
        Analysis DataFrame
    
    Raises:
        FileNotFoundError: If cached file doesn't exist (need to rebuild)
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Cached dataset not found at {input_path}. "
            f"Please rebuild with: python -m src.dashboard.app --rebuild-dataset"
        )
    
    df = pd.read_csv(input_path)
    print(f"✓ Loaded cached dataset: {len(df):,} rows, {df['iso_code'].nunique()} countries")
    return df


if __name__ == '__main__':
    # Build and save dataset
    df = build_analysis_dataset()
    save_analysis_dataset(df)
    
    # Test load
    print("\nTesting load...")
    df_loaded = load_analysis_dataset()
    print(f"✓ Load successful: {len(df_loaded):,} rows")
