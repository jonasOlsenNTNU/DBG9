# Data Processing Utilities

This directory contains expensive data processing operations that should **only run when rebuilding the dataset**.

## Files

- **`maritime_classifier.py`** - Classifies countries into maritime intensity tiers
- **`data_pipeline.py`** - ETL pipeline to build analysis-ready dataset
- **`build_dataset.py`** - CLI script for dataset rebuild

## Usage

### Rebuild Dataset

**Option 1: Via main app (recommended)**
```bash
python -m src.dashboard.app --rebuild-dataset
```

**Option 2: Direct CLI**
```bash
cd src/utils
python build_dataset.py [options]
```

**Options:**
- `--no-interpolate` - Skip interpolation of missing values
- `--max-gap N` - Maximum gap to interpolate (default: 2 years)
- `--start-year YYYY` - Start year (default: 2000)
- `--end-year YYYY` - End year (default: 2024)
- `--output PATH` - Output path (default: data/analysis_ready.csv)

### When to Rebuild

Rebuild the dataset when:
- Source data files updated (`owid-co2-data.csv`, `port_traffic_data.csv`, `oecd.csv`)
- Classification logic changes (modifying thresholds, adding tiers)
- New derived metrics added
- Interpolation parameters change

**Typical runtime:** 30-60 seconds

## Output

**File:** `data/analysis_ready.csv`

**Contents:**
- Country identifiers (iso_code, country_name)
- Time dimension (year, 2000-2024)
- Port metrics (port_traffic, teu_per_capita, teu_per_gdp)
- CO₂ metrics (co2, co2_per_capita, co2_per_gdp, co2_per_teu)
- Sectoral breakdown (coal_co2, oil_co2, cement_co2, gas_co2, shares)
- Derived metrics (port_cagr_7y, co2_cagr_7y, decoupling_index)
- Maritime classification (maritime_tier: china/high/medium-high/medium-low/low)
- Data quality flags (data_quality: complete/interpolated/sparse)
- Interpolation flags (has_interpolated_port_traffic)

**Size:** ~5-10 MB

## Maritime Classification Logic

Countries classified based on 2022 data using:

**Metrics:**
- TEU per capita (port traffic / population)
- TEU per GDP (port traffic / GDP in millions)
- Absolute TEU (total port traffic)

**Tiers:**
1. **China** - Standalone (dominates with 56% port, 59% CO₂ of current TOP10)
2. **High maritime** - Top 25% TEU/capita AND top 33% absolute volume
3. **Medium-high** - Top 25% TEU/capita OR top 33% absolute volume
4. **Low maritime** - Bottom 25% TEU/capita AND bottom 33% absolute volume
5. **Medium-low** - Everything else

**Quality filters:**
- Minimum 15 years of data (2000-2022 period)
- Maximum 3 consecutive missing years
- Countries failing filters excluded from analysis

## Data Filtering & Removal

**What gets removed from source data:**

1. **Landlocked & non-maritime countries**
   - Examples: Afghanistan, Armenia, Bolivia, Botswana, Ethiopia, Hungary
   - These have no port traffic data → excluded from merge
   - **Rationale:** Research focuses on maritime economies; landlocked countries have no shipping infrastructure

2. **Countries with zero port traffic**
   - Filtered via `port_traffic > 0` check
   - Typical for territories with no commercial ports
   - **Rationale:** Can't classify by maritime intensity without port activity

3. **Sparse data (quality filter)**
   - Countries with insufficient years of coverage in analysis period
   - Countries with excessive consecutive missing years
   - Set to `maritime_tier = NaN` in output (kept as rows for reference)
   - **Rationale:** Insufficient data for reliable classification or trend analysis

4. **OWID aggregates**
   - Filtered to 3-letter ISO codes only (removes "World", "OECD", regional groups)
   - **Rationale:** Analysis uses individual countries only

**Result:** Majority of output rows are countries with maritime data (port traffic ≥ 0)

## Data Quality Handling

**Interpolation:**
- Fills gaps ≤2 consecutive years using linear interpolation
- Only applied within country time series (not across countries)
- Flagged in `has_interpolated_*` columns

**Quality tiers:**
- `complete` - No missing data, no interpolation
- `interpolated` - Some gaps filled (≤2 years)
- `sparse` - >3 consecutive gaps or <15 total years (marked as NaN maritime_tier)

## Testing

Test maritime classifier:
```bash
cd src/utils
python maritime_classifier.py
```

Test data pipeline:
```bash
cd src/utils
python data_pipeline.py
```

## Integration with Dashboard

**Dashboard loads from cached CSV:**
```python
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parents[2] / "data"
df = pd.read_csv(DATA_DIR / "analysis_ready.csv")
```

**Never call `build_analysis_dataset()` from dashboard code** - this is expensive and defeats the caching strategy.

## Development Notes

**Adding new metrics:**
1. Add calculation to `calculate_derived_metrics()` in `data_pipeline.py`
2. Add column to final column list
3. Rebuild dataset
4. Update dashboard views to use new metric

**Changing classification:**
1. Modify `classify_maritime_intensity()` in `maritime_classifier.py`
2. Rebuild dataset
3. Verify tier distribution in output

**Performance:**
- Most time spent in pandas merge operations (~20s)
- OWID file is large (~50MB, 50K rows)
- Consider caching intermediate merges if rebuild becomes bottleneck
