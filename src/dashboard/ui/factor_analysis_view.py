# src/dashboard/ui/factor_analysis_view.py
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas  # noqa: F401
from ..utils.load_css import load_css


DEFAULT_OUTCOME = "co2_per_teu"
DEFAULT_PREDICTORS = [
    "energy_per_gdp",
    "energy_per_capita",
    "coal_share",
    "oil_share",
    "cement_share",
    "gas_share",
    "gdp_per_capita",
]


def _available_predictors(df: pd.DataFrame, predictors: List[str]) -> List[str]:
    return [p for p in predictors if p in df.columns]


def create_factor_correlation_matrix(
        df: pd.DataFrame,
        outcome_var: str = DEFAULT_OUTCOME,
        predictor_vars: List[str] | None = None,
) -> pn.Column:
    """
    Interactive correlation heatmap between one outcome and a set of predictors.
    """
    if predictor_vars is None:
        predictor_vars = _available_predictors(df, DEFAULT_PREDICTORS)
    else:
        predictor_vars = _available_predictors(df, predictor_vars)

    cols = [c for c in [outcome_var] + predictor_vars if c in df.columns]
    sub = df[cols].dropna()

    if sub.empty or len(cols) < 2:
        return pn.Column("No data for selected variables.")

    corr = sub.corr()
    corr_long = (
        corr.reset_index()
        .melt(id_vars="index", var_name="var2", value_name="corr")
        .rename(columns={"index": "var1"})
    )

    heatmap = corr_long.hvplot.heatmap(
        x="var1",
        y="var2",
        C="corr",
        clim=(-1, 1),
        cmap="RdBu_r",
        colorbar=True,
        title="Correlation matrix",
        width=600,
        height=500,
    )

    return pn.Column(
        pn.pane.HoloViews(heatmap, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )



def create_regression_summary(
        df: pd.DataFrame,
        outcome: str,
        predictors: List[str],
        controls: List[str] | None = None,
) -> pn.widgets.Tabulator:
    """
    Simplified regression-like summary:
    For each predictor, estimate a simple slope d(outcome)/d(predictor) using OLS on that pair.
    (This is not full panel regression but matches the idea of effect direction and strength.)
    """
    if controls is None:
        controls = []

    rows = []
    for var in predictors:
        if var not in df.columns:
            continue
        sub = df[[outcome, var]].dropna()
        if len(sub) < 10:
            continue

        x = sub[var].to_numpy(dtype=float)
        y = sub[outcome].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)

        rows.append(
            {
                "variable": var,
                "coef": slope,
                "intercept": intercept,
                "n_obs": len(sub),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        result = pd.DataFrame(
            [{"variable": "(no predictors with enough data)", "coef": np.nan, "intercept": np.nan, "n_obs": 0}]
        )

    return pn.widgets.Tabulator(
        result,
        pagination="local",
        page_size=15,
        sizing_mode="stretch_width",
        height=360,
    )


def create_success_factors_tab(df: pd.DataFrame) -> pn.Column:
    """
    Full 'Success Factors' tab: choose outcome & year, see correlation heatmap and simple coefficient table.
    """
    load_css("main_view.css")

    header = pn.pane.Markdown(
        """
# Success factors in maritime decarbonisation

This section explores **which structural characteristics** (income level, region, fuel mix, etc.)
are most strongly associated with **low CO₂ per TEU** or **low CO₂ per capita**.

Use it to identify **patterns** rather than to claim strict causality.
        """,
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )

    years = sorted(df["year"].unique())
    year_select = pn.widgets.IntSlider(
        name="Year",
        start=min(years),
        end=max(years),
        value=max(years),
    )

    outcome_select = pn.widgets.Select(
        name="Outcome variable",
        options=[
            "co2_per_teu",      # CO₂ per TEU (efficiency)
            "co2_per_capita",   # CO₂ per capita
            "decoupling_index", # Decoupling index (7-year)
            "co2_cagr_7y",      # CO₂ CAGR 7-year
        ],
        value="co2_per_teu",
    )

    all_predictors = _available_predictors(df, DEFAULT_PREDICTORS)
    predictor_select = pn.widgets.MultiChoice(
        name="Predictors",
        options=all_predictors,
        value=all_predictors[:4],
        width=350,
    )

    @pn.depends(year_select.param.value, outcome_select.param.value, predictor_select.param.value)
    def _correlation_view(year, outcome, predictors):
        sub = df[df["year"] == year]
        return create_factor_correlation_matrix(
            sub,
            outcome_var=outcome,
            predictor_vars=list(predictors),
        )

    @pn.depends(year_select.param.value, outcome_select.param.value, predictor_select.param.value)
    def _regression_view(year, outcome, predictors):
        sub = df[df["year"] == year]
        return create_regression_summary(
            sub,
            outcome=outcome,
            predictors=list(predictors),
        )

    @pn.depends(year_select.param.value, outcome_select.param.value, predictor_select.param.value)
    def _insights(year, outcome, predictors):
        sub = df[df["year"] == year]
        if outcome not in sub.columns:
            return pn.pane.Markdown("**Key insights**\n\nOutcome not available.")

        sub = sub[[outcome] + [p for p in predictors if p in sub.columns]].dropna()
        if sub.empty:
            return pn.pane.Markdown("**Key insights**\n\nNo overlapping data for selected variables.")

        corr = sub.corr()[outcome].drop(outcome).sort_values(ascending=False)
        top_pos = corr.head(2)
        top_neg = corr.tail(2)

        def _fmt(series, label):
            if series.empty:
                return f"- No clear {label} correlations."
            lines = []
            for name, val in series.items():
                lines.append(f"- **{name}**: corr = {val:.2f}")
            return "\n".join(lines)

        text = (
            "### Key insights\n\n"
            f"**Year:** {year}\n\n"
            f"Strong positive correlations with {outcome}:\n"
            f"{_fmt(top_pos, 'positive')}\n\n"
            f"Strong negative correlations with {outcome}:\n"
            f"{_fmt(top_neg, 'negative')}"
        )
        return pn.pane.Markdown(text)

    controls = pn.Row(
        year_select,
        outcome_select,
        predictor_select,
        sizing_mode="stretch_width",
    )


    content_card = pn.Column(
        controls,
        pn.Row(_correlation_view, _regression_view, sizing_mode="stretch_width"),
        _insights,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    return pn.Column(
        header,
        content_card,
        sizing_mode="stretch_width",
        css_classes=["story-layout"],
    )