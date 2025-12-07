"""
CLI script to rebuild the analysis dataset.

Usage:
    python src/utils/build_dataset.py [options]

Options:
    --no-interpolate    Skip interpolation of missing values
    --max-gap N         Maximum gap size to interpolate (default: 2)
    --start-year YYYY   Start year (default: 2000)
    --end-year YYYY     End year (default: 2024)

This script rebuilds data/analysis_ready.csv from source files.
Typical runtime: 30-60 seconds depending on system.
"""

import argparse
from pathlib import Path

from .data_pipeline import build_analysis_dataset, save_analysis_dataset

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "data" / "analysis_ready.csv"


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild analysis dataset from source data"
    )
    parser.add_argument(
        '--no-interpolate',
        action='store_true',
        help='Skip interpolation of missing values'
    )
    parser.add_argument(
        '--max-gap',
        type=int,
        default=2,
        help='Maximum consecutive years to interpolate (default: 2)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2000,
        help='Start year for dataset (default: 2000)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2024,
        help='End year for dataset (default: 2024)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=OUTPUT_PATH,
        help=f'Output path (default: {OUTPUT_PATH})'
    )
    
    args = parser.parse_args()
    
    # Build dataset
    df = build_analysis_dataset(
        interpolate=not args.no_interpolate,
        max_gap=args.max_gap,
        year_range=(args.start_year, args.end_year)
    )
    
    # Save
    save_analysis_dataset(df, args.output)
    
    print("\n✅ Dataset rebuild complete!")
    print(f"   Dashboard can now load from: {args.output}")


if __name__ == '__main__':
    main()
