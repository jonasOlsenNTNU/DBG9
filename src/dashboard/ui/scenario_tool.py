# src/dashboard/ui/scenario_tool.py
from __future__ import annotations

import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas  # noqa: F401


def _calculate_baseline_projection(
    df: pd.DataFrame, iso_code: str, target_year: int = 2030
) -> dict:
    """
    Calculate baseline 2030 projection using historical trends.
    
    Uses 2015-2022 CAGR for port traffic and CO2 to project forward.
    """
    country_df = df[df["iso_code"] == iso_code].sort_values("year")
    
    if country_df.empty:
        return None
    
    # Get most recent data point
    latest = country_df.iloc[-1]
    latest_year = int(latest["year"])
    
    # Calculate historical CAGR (2015-2022 or available range)
    historical = country_df[country_df["year"] >= 2015]
    
    if len(historical) < 2:
        # Not enough data for projection
        return None
    
    first = historical.iloc[0]
    last = historical.iloc[-1]
    years_diff = int(last["year"] - first["year"])
    
    if years_diff == 0:
        return None
    
    # Calculate CAGRs
    port_cagr = 0.0
    co2_cagr = 0.0
    gdp_cagr = 2.0  # Default assumption
    efficiency_cagr = 0.0  # CO2/TEU improvement rate
    
    if first["port_traffic"] > 0 and last["port_traffic"] > 0:
        port_cagr = (last["port_traffic"] / first["port_traffic"]) ** (1 / years_diff) - 1
    
    if first["co2"] > 0 and last["co2"] > 0:
        co2_cagr = (last["co2"] / first["co2"]) ** (1 / years_diff) - 1
    
    if first["gdp"] > 0 and last["gdp"] > 0:
        gdp_cagr = (last["gdp"] / first["gdp"]) ** (1 / years_diff) - 1
    
    # Calculate CO2/TEU efficiency improvement rate
    first_co2_per_teu = (first["co2"] * 1e6) / first["port_traffic"] if first["port_traffic"] > 0 else 0
    last_co2_per_teu = (last["co2"] * 1e6) / last["port_traffic"] if last["port_traffic"] > 0 else 0
    
    if first_co2_per_teu > 0 and last_co2_per_teu > 0:
        efficiency_cagr = (last_co2_per_teu / first_co2_per_teu) ** (1 / years_diff) - 1
    
    # Project to target year
    years_to_project = target_year - latest_year
    
    baseline_port = latest["port_traffic"] * (1 + port_cagr) ** years_to_project
    baseline_co2 = latest["co2"] * (1 + co2_cagr) ** years_to_project
    baseline_gdp = latest["gdp"] * (1 + gdp_cagr) ** years_to_project
    baseline_co2_per_teu = (baseline_co2 * 1e6) / baseline_port if baseline_port > 0 else 0
    
    # Calculate historical coal transition rate
    first_coal = first.get("coal_share", 0)
    last_coal = last.get("coal_share", 0)
    coal_change_pp_per_year = (last_coal - first_coal) / years_diff if years_diff > 0 else 0
    
    return {
        "country": latest["country"],
        "latest_year": latest_year,
        "latest_port": latest["port_traffic"],
        "latest_co2": latest["co2"],
        "latest_gdp": latest["gdp"],
        "latest_co2_per_teu": latest["co2_per_teu"],
        "coal_share": latest.get("coal_share", 0),
        "gas_share": latest.get("gas_share", 0),
        "oil_share": latest.get("oil_share", 0),
        "port_cagr": port_cagr * 100,  # as percentage
        "co2_cagr": co2_cagr * 100,
        "gdp_cagr": gdp_cagr * 100,
        "efficiency_cagr": efficiency_cagr * 100,  # CO2/TEU improvement rate
        "coal_change_rate": coal_change_pp_per_year,  # pp per year
        "baseline_port_2030": baseline_port,
        "baseline_co2_2030": baseline_co2,
        "baseline_gdp_2030": baseline_gdp,
        "baseline_co2_per_teu_2030": baseline_co2_per_teu,
    }


def _calculate_adjusted_projection(
    baseline: dict,
    efficiency_acceleration: float,  # Multiplier for historical efficiency improvement rate (1.0 = continue trend)
    coal_transition_speed: float,  # Multiplier for coal phase-out rate (1.0 = continue historical)
    target_year: int = 2030,
) -> dict:
    """
    Calculate adjusted projection using data-driven parameters.
    
    Args:
        baseline: Baseline projection dict with historical trends
        efficiency_acceleration: Multiplier for CO2/TEU improvement (e.g., 2.0 = double historical rate)
        coal_transition_speed: Multiplier for coal phase-out (e.g., 2.0 = twice as fast as historical)
    
    Returns:
        Dict with adjusted projections and impact breakdown
    """
    if baseline is None:
        return None
    
    years_to_project = target_year - baseline["latest_year"]
    
    # Port traffic: keep baseline (no adjustment - focus on efficiency)
    adjusted_port = baseline["baseline_port_2030"]
    adjusted_port_cagr = baseline["port_cagr"]
    
    # Efficiency improvement: accelerate historical CO2/TEU improvement rate
    baseline_efficiency_cagr = baseline["efficiency_cagr"] / 100
    adjusted_efficiency_cagr = baseline_efficiency_cagr * efficiency_acceleration
    
    # Project CO2/TEU efficiency
    adjusted_co2_per_teu = baseline["latest_co2_per_teu"] * (1 + adjusted_efficiency_cagr) ** years_to_project
    
    # Coal transition impact (empirical from energy mix change)
    historical_coal_rate = baseline["coal_change_rate"]  # pp per year
    adjusted_coal_rate = historical_coal_rate * coal_transition_speed
    coal_reduction_pp = adjusted_coal_rate * years_to_project
    
    # Estimate CO2 impact from coal transition
    # Coal is ~2.3x more CO2-intensive than gas per MWh
    # If coal → gas: ~57% reduction per pp of coal share
    # If coal → renewable: ~100% reduction per pp
    # Assume mix: 70% gas, 30% renewable = ~70% reduction
    current_coal_share = baseline["coal_share"]
    coal_reduction_actual = min(abs(coal_reduction_pp), current_coal_share)  # Can't reduce more than current share
    
    # CO2 reduction from coal transition (conservative: assume coal → gas mostly)
    co2_from_coal_transition = 0.0
    if current_coal_share > 0 and coal_reduction_actual != 0:
        # Proportional impact: if 10pp coal → gas, ~6% total CO2 reduction for 30% coal share
        coal_contribution = current_coal_share / 100  # Coal's share of total emissions
        co2_from_coal_transition = baseline["baseline_co2_2030"] * (coal_reduction_actual / 100) * 0.57
    
    # Calculate total CO2 from efficiency + energy mix
    # Method: CO2 = Port × CO2/TEU, then adjust for coal transition
    co2_from_efficiency = (adjusted_port * adjusted_co2_per_teu) / 1e6
    adjusted_co2 = co2_from_efficiency - co2_from_coal_transition
    adjusted_co2 = max(adjusted_co2, 0)  # Can't be negative
    
    # Recalculate efficiency metric
    adjusted_co2_per_teu_final = (adjusted_co2 * 1e6) / adjusted_port if adjusted_port > 0 else 0
    
    # Calculate implied CO2 CAGR
    if baseline["latest_co2"] > 0:
        adjusted_co2_cagr = ((adjusted_co2 / baseline["latest_co2"]) ** (1 / years_to_project) - 1) * 100
    else:
        adjusted_co2_cagr = 0.0
    
    # Efficiency improvement percentage
    efficiency_improvement_pct = ((baseline["latest_co2_per_teu"] - adjusted_co2_per_teu_final) / 
                                  baseline["latest_co2_per_teu"] * 100) if baseline["latest_co2_per_teu"] > 0 else 0
    
    return {
        "adjusted_port_2030": adjusted_port,
        "adjusted_co2_2030": adjusted_co2,
        "adjusted_co2_per_teu_2030": adjusted_co2_per_teu_final,
        "adjusted_port_cagr": adjusted_port_cagr,
        "adjusted_co2_cagr": adjusted_co2_cagr,
        "adjusted_efficiency_cagr": adjusted_efficiency_cagr * 100,
        "efficiency_improvement_pct": efficiency_improvement_pct,
        "coal_reduction_pp": coal_reduction_actual,
        "co2_reduction_vs_baseline": baseline["baseline_co2_2030"] - adjusted_co2,
        "co2_reduction_pct": ((baseline["baseline_co2_2030"] - adjusted_co2) / baseline["baseline_co2_2030"] * 100) 
            if baseline["baseline_co2_2030"] > 0 else 0.0,
        "co2_from_efficiency": baseline["baseline_co2_2030"] - co2_from_efficiency,
        "co2_from_coal_transition": co2_from_coal_transition,
    }


def create_scenario_visualization(
    country_slice: pd.DataFrame,
    iso_code: str,
    baseline: dict,
    adjusted: dict,
    target_year: int = 2030,
):
    """
    Create timeline visualization showing historical + projected paths.
    Optimized for performance with numpy arrays and single plot.
    
    Args:
        country_slice: Pre-filtered DataFrame for single country (year, co2 columns only)
        iso_code: Country ISO code (for reference)
        baseline: Baseline projection dict
        adjusted: Adjusted projection dict
        target_year: Projection target year
    """
    if baseline is None or adjusted is None:
        return pn.pane.Markdown("Insufficient data for projection.")
    
    # Use numpy arrays for speed - data is already filtered
    historical_years = country_slice["year"].values.astype(int)
    historical_co2 = country_slice["co2"].values.astype(float)
    
    latest_year = int(baseline["latest_year"])
    latest_co2 = baseline["latest_co2"]
    
    # Build arrays efficiently
    n_hist = len(historical_years)
    
    # Combine all data in single arrays (faster than list append)
    years = np.concatenate([
        historical_years,                    # Historical
        [latest_year, target_year],          # Baseline projection
        [latest_year, target_year],          # Adjusted projection
    ])
    
    co2_values = np.concatenate([
        historical_co2,                      # Historical
        [latest_co2, baseline["baseline_co2_2030"]],  # Baseline
        [latest_co2, adjusted["adjusted_co2_2030"]],  # Adjusted
    ])
    
    scenarios = (
        ["Historical"] * n_hist +
        ["Baseline 2030"] * 2 +
        ["Adjusted 2030"] * 2
    )
    
    # Single DataFrame creation (faster than list of dicts)
    proj_df = pd.DataFrame({
        "year": years,
        "co2": co2_values,
        "scenario": scenarios,
    })
    
    # Color mapping for scenarios
    color_key = {
        "Historical": "black",
        "Baseline 2030": "gray",
        "Adjusted 2030": "blue",
    }
    
    # Single plot with by parameter (more efficient than overlay)
    plot = proj_df.hvplot.line(
        x="year",
        y="co2",
        by="scenario",
        line_width=2,
        color_key=color_key,
    ).opts(
        xlabel="Year",
        ylabel="CO₂ (Mt)",
        title=f"CO₂ Projection – {baseline['country']}",
        height=400,
        width=800,
        show_grid=True,
        legend_position="top_right",
        toolbar=None,  # Disable toolbar for better performance
        responsive=False,  # Fixed size for consistent performance
    )
    
    return pn.pane.HoloViews(plot, sizing_mode="stretch_width")


def create_scenario_widget(df: pd.DataFrame) -> pn.Column:
    """
    Interactive scenario modeling widget with sliders and projections.
    """
    # Get list of countries with sufficient data
    countries_with_data = []
    for iso in df["iso_code"].unique():
        baseline = _calculate_baseline_projection(df, iso)
        if baseline is not None:
            countries_with_data.append((baseline["country"], iso))
    
    countries_with_data.sort()
    
    if not countries_with_data:
        return pn.Column("No countries with sufficient data for projections.")
    
    # Default to first country (or Norway if available)
    default_country = next(
        (iso for name, iso in countries_with_data if name == "Norway"),
        countries_with_data[0][1]
    )
    
    # Widgets
    country_select = pn.widgets.Select(
        name="Country",
        options={name: iso for name, iso in countries_with_data},
        value=default_country,
        width=300,
    )
    
    efficiency_acceleration = pn.widgets.FloatSlider(
        name="Efficiency improvement acceleration",
        start=0.0,
        end=3.0,
        step=0.25,
        value=1.0,
        width=400,
    )
    
    coal_transition_speed = pn.widgets.FloatSlider(
        name="Coal phase-out acceleration",
        start=0.0,
        end=3.0,
        step=0.25,
        value=1.0,
        width=400,
    )
    
    # Pre-filter and cache country data for performance
    country_data_cache = {}
    for iso in df["iso_code"].unique():
        country_slice = df[df["iso_code"] == iso][["year", "co2"]].sort_values("year")
        if not country_slice.empty:
            country_data_cache[iso] = country_slice
    
    def _view(iso, eff_accel, coal_speed):
        """Generate scenario view for selected parameters."""
        baseline = _calculate_baseline_projection(df, iso)
        
        if baseline is None:
            return pn.pane.Markdown("⚠️ Insufficient historical data for this country.")
        
        adjusted = _calculate_adjusted_projection(
            baseline, eff_accel, coal_speed, target_year=2030
        )
        
        # Historical efficiency trend description
        eff_trend = "improving" if baseline['efficiency_cagr'] < 0 else "worsening"
        coal_trend = "declining" if baseline['coal_change_rate'] < 0 else "increasing"
        
        # Country-specific scenario context
        method_text = f"""
### {baseline['country']} – Historical Trends (2015–{baseline['latest_year']})

**Efficiency trajectory:** CO₂/TEU is {eff_trend} at **{abs(baseline['efficiency_cagr']):.2f}%/year**  
**Energy transition:** Coal share {coal_trend} at **{abs(baseline['coal_change_rate']):.2f} pp/year**  
**Current status:** {'✓ Decoupling' if baseline['efficiency_cagr'] < 0 else '✗ Still coupling'} 
({'emissions falling' if baseline['co2_cagr'] < 0 else 'emissions rising'} at {abs(baseline['co2_cagr']):.2f}%/year)

**Your scenario:** Efficiency {eff_accel:.2f}× | Coal transition {coal_speed:.2f}×
"""
        
        # Summary statistics
        summary_text = f"""
---

**Historical baseline ({baseline['latest_year']}):**
- Port traffic: **{baseline['latest_port']:,.0f} TEU** (growing {baseline['port_cagr']:.2f}%/year)
- CO₂ emissions: **{baseline['latest_co2']:.2f} Mt** ({baseline['co2_cagr']:+.2f}%/year)
- CO₂/TEU efficiency: **{baseline['latest_co2_per_teu']:.2f} kg/TEU**
- Energy mix: Coal {baseline['coal_share']:.1f}%, Gas {baseline['gas_share']:.1f}%, Oil {baseline['oil_share']:.1f}%

**Baseline 2030 projection (business as usual):**
- Port: {baseline['baseline_port_2030']:,.0f} TEU
- CO₂: {baseline['baseline_co2_2030']:.2f} Mt
- CO₂/TEU: {baseline['baseline_co2_per_teu_2030']:.2f} kg/TEU

**Adjusted 2030 scenario (with policy acceleration):**
- Port: {adjusted['adjusted_port_2030']:,.0f} TEU
- CO₂: **{adjusted['adjusted_co2_2030']:.2f} Mt** ({adjusted['adjusted_co2_cagr']:.2f}%/year)
- CO₂/TEU: **{adjusted['adjusted_co2_per_teu_2030']:.2f} kg/TEU** ({adjusted['adjusted_efficiency_cagr']:.2f}%/year)
- Efficiency improvement: **{adjusted['efficiency_improvement_pct']:.1f}%** vs {baseline['latest_year']}
- Coal reduction: {adjusted['coal_reduction_pp']:.1f} pp

**Decoupling impact vs baseline:**
- Total CO₂ reduction: **{adjusted['co2_reduction_vs_baseline']:.2f} Mt** ({adjusted['co2_reduction_pct']:.1f}%)
  - From efficiency improvements: {adjusted['co2_from_efficiency']:.2f} Mt
  - From coal energy transition: {adjusted['co2_from_coal_transition']:.2f} Mt
        """
        
        method = pn.pane.Markdown(method_text, sizing_mode="stretch_width")
        summary = pn.pane.Markdown(summary_text, sizing_mode="stretch_width")
        
        # Visualization - use cached country data slice
        country_slice = country_data_cache.get(iso)
        if country_slice is not None:
            viz = create_scenario_visualization(country_slice, iso, baseline, adjusted)
        else:
            viz = pn.pane.Markdown("⚠️ No data available for visualization.")
        
        # Return content with visualization first, then details
        return pn.Column(
            viz,
            method,
            summary,
            sizing_mode="stretch_width",
        )
    
    # Bind dynamic view
    dynamic_panel = pn.bind(
        _view,
        iso=country_select,
        eff_accel=efficiency_acceleration,
        coal_speed=coal_transition_speed,
    )
    
    return pn.Column(
        "## 2030 Scenario Modeling",
        pn.pane.Markdown(
            """
This tool models **maritime decoupling scenarios** – reducing CO₂ emissions while maintaining 
or growing port traffic through improved **CO₂/TEU efficiency**.

### How to use:
1. Select a country to see its historical efficiency trend (2015–2022)
2. Adjust the **multipliers** to model policy acceleration scenarios
3. Compare projections: **Baseline** (continue trend) vs **Adjusted** (accelerated policies)

### Reading the graph:
- **Blue**: Historical emissions | **Red**: Baseline 2030 | **Yellow**: Adjusted 2030
- **Downward trend**: Decoupling success (emissions ↓ despite port growth)
- **Gap size**: Policy impact magnitude

**Multipliers:** 1.0× = continue historical trend | 2.0× = double improvement rate | 0.0× = stagnation
            """,
            sizing_mode="stretch_width",
        ),
        pn.pane.Markdown("---\n### Policy intervention scenarios:"),
        country_select,
        efficiency_acceleration,
        coal_transition_speed,
        dynamic_panel,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )


def create_scenario_tab(df: pd.DataFrame) -> pn.Column:
    """
    Tab 7: 2030 scenario modeling tool.
    """
    return create_scenario_widget(df)

