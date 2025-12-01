from __future__ import annotations

import panel as pn
import pandas as pd

from .plot_generator import (
    make_total_co2_plot,
    make_total_co2_index_plot,
    make_intensity_plot,
    make_ratio_plot,
    make_forecast_plot,
)


def create_header():
    return pn.pane.Markdown(
        """
# How do CO₂ emissions differ between highly maritime and low-maritime economies?

We analyse two groups of countries based on their role in the global maritime system:

- **Top 10 maritime economies** — large ports, strong shipping sectors and high trade volumes.
- **Bottom 10 coastal economies** — countries with significantly lower maritime activity and throughput.

Using the OWID CO₂ dataset, this dashboard examines how these two groups differ in:

- **Total CO₂ emissions** and their evolution since 2000.  
- **Emission intensity**, measured per GDP and per capita.  
- **Top/Bottom ratios**, showing whether maritime-heavy economies are diverging or converging over time.

_This provides a data-driven foundation for linking maritime activity with national CO₂ patterns._
        """,
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )


def create_key_messages():
    return pn.pane.HTML(
        """
<div class="key-messages">
  <div class="key-message-card">
    CO₂ emissions in top maritime economies have grown moderately since 2000,
    but remain far higher than in bottom-tier economies.
  </div>
  <div class="key-message-card">
    Emission intensity (per GDP or per capita) shows different patterns across groups,
    suggesting structural economic differences.
  </div>
  <div class="key-message-card">
    Maritime activity correlates with both CO₂ and container throughput,
    especially for high-volume trade nations.
  </div>
</div>
        """,
        sizing_mode="stretch_width",
    )


def create_controls_row(intensity_widget: pn.widgets.Select):
    return pn.Row(
        pn.pane.Markdown(
            "Intensity metric (section 2):", sizing_mode="fixed"
        ),
        intensity_widget,
        sizing_mode="stretch_width",
    )


def create_section_total(df: pd.DataFrame):
    total_abs_plot = make_total_co2_plot(df)
    total_index_plot = make_total_co2_index_plot(df)

    return pn.Column(
        pn.pane.Markdown(
            "### 1. Total CO₂ over time\n"
            "_Top panel: absolute average total CO₂ emissions per country in each group (Mt)._  \n"
            "_Bottom panel: indexed view (first year = 1) so we can compare **relative growth**._"
        ),
        total_abs_plot,
        pn.pane.Markdown("_Indexed growth (first year = 1)_"),
        total_index_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )


def create_section_intensity(df: pd.DataFrame, intensity_widget: pn.widgets.Select):
    # bind intensitetsplottet til dropdownen
    intensity_plot = pn.bind(
        lambda metric: make_intensity_plot(df, metric),
        metric=intensity_widget,
    )

    return pn.Column(
        pn.pane.Markdown(
            "### 2. Emission intensity over time\n"
            "_Compare how emission **intensity** (per capita or per GDP) evolves "
            "for the two groups. Use the selector above to switch metric._"
        ),
        intensity_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )


def create_section_ratio(df: pd.DataFrame):
    ratio_plot = make_ratio_plot(df)

    return pn.Column(
        pn.pane.Markdown(
            "### 3. Top / Bottom CO₂ ratio\n"
            "_How many times higher are emissions in the Top 10 group compared to "
            "the Bottom 10 group? Values above 1 mean Top 10 emits more._"
        ),
        ratio_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )


def create_forecast_section(df: pd.DataFrame):
    forecast_plot, mae_naive, mae_lin = make_forecast_plot(df)

    info = pn.pane.Markdown(
        f"""
### 4. Short-term forecast for Top 10 CO₂  

We fit two simple models to the Top 10 maritime economies' total CO₂ emissions
(from 1960 onwards) and forecast the next **3 years**:

- **Naive model:** extends the last observed value forward.  
- **Linear trend model:** fits a straight line to recent decades and extrapolates.

Backtesting on the last 3 observed years gives:

- Mean absolute error (MAE), naive model: **{mae_naive:,.1f} Mt**  
- Mean absolute error (MAE), linear model: **{mae_lin:,.1f} Mt**

In the written report you can discuss which model you find more realistic and
how the limited temporal resolution (annual data) affects short-term forecasts.
""",
        sizing_mode="stretch_width",
    )

    return pn.Column(
        info,
        forecast_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )
