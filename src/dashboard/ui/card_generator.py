from __future__ import annotations

from pathlib import Path
from functools import lru_cache
import panel as pn
import pandas as pd

from .plot_generator import (
    make_total_co2_index_multi_plot,
    make_ratio_plot,
    make_forecast_plot,
    make_total_co2_log_plot,
    make_total_co2_multi_plot,
    make_intensity_multi_plot,
    make_intensity_index_multi_plot,
    FORECAST_SERIES_MAP
)

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
CO2_PATH = DATA_DIR / "owid-co2-data.csv"


@lru_cache()
def _load_owid_co2_for_total() -> pd.DataFrame:
    df = pd.read_csv(CO2_PATH, usecols=["country", "year", "co2"])
    df = df.dropna(subset=["co2"])
    df["year"] = df["year"].astype(int)
    return df

@lru_cache()
def _load_owid_co2_for_intensity() -> pd.DataFrame:
    df = pd.read_csv(
        CO2_PATH,
        usecols=[
            "country",
            "year",
            "co2",
            "co2_per_capita",
            "co2_per_gdp",
            "population",
            "gdp",
        ],
    )
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    return df




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
    co2_all = _load_owid_co2_for_total()

    min_year = int(df["year"].min())
    max_year = int(df["year"].max())
    co2_all = co2_all[
        (co2_all["year"] >= min_year) & (co2_all["year"] <= max_year)
        ]

    group_labels = ["Top 10 maritime (avg)", "Bottom 10 coastal (avg)"]

    country_labels = sorted(co2_all["country"].unique().tolist())

    options = group_labels + country_labels

    series_selector = pn.widgets.MultiChoice(
        name="Groups / countries / regions",
        value=group_labels,
        options=options,
        placeholder="Type to search (e.g. Norway)",
        width=400,
    )

    total_dynamic_plot = pn.bind(
        make_total_co2_multi_plot,
        df_groups=df,
        df_countries=co2_all,
        selected_labels=series_selector,
    )

    total_index_plot = pn.bind(
        make_total_co2_index_multi_plot,
        df_groups=df,
        df_countries=co2_all,
        selected_labels=series_selector,
    )

    heading = pn.pane.Markdown(
        """
### 1. Total CO₂ over time

Top panel: choose **Top 10 / Bottom 10** and any single countries or regions to compare.  
Bottom panel: indexed view (first year = 1) so we can compare **relative growth**.

**Reflection – what this section shows**

- The **Top-10 maritime economies** dominate total CO₂ levels, with steep growth after around 1950 and especially since 2000.  
- The **Bottom-10 coastal economies** emit far less in absolute terms, but their indexed series reveals strong **relative growth** as late-comer maritime economies expand.  
- Together, the panels support a narrative where high-maritime economies drive the current emissions stock, while growth in lower-tier coastal economies matters increasingly for future trends.
        """,
        sizing_mode="stretch_width",
    )

    return pn.Column(
        heading,
        series_selector,
        total_dynamic_plot,
        total_index_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

def create_section_intensity(df: pd.DataFrame):
    co2_int = _load_owid_co2_for_intensity()


    min_year = int(df["year"].min())
    max_year = int(df["year"].max())
    co2_int = co2_int[
        (co2_int["year"] >= min_year) & (co2_int["year"] <= max_year)
        ]

    group_labels = ["Top 10 maritime (avg)", "Bottom 10 coastal (avg)"]
    country_labels = sorted(co2_int["country"].unique().tolist())
    options = group_labels + country_labels

    series_selector = pn.widgets.MultiChoice(
        name="Groups / countries / regions",
        value=group_labels,
        options=options,
        placeholder="Type to search (e.g. Norway)",
        width=400,
    )

    metric_selector = pn.widgets.RadioButtonGroup(
        name="Intensity metric",
        options=["per_capita", "per_100k", "per_gdp"],
        value="per_capita",
        button_type="default",
    )

    intensity_plot = pn.bind(
        make_intensity_multi_plot,
        df_groups=df,
        df_countries=co2_int,
        selected_labels=series_selector,
        metric=metric_selector,
    )

    intensity_index_plot = pn.bind(
        make_intensity_index_multi_plot,
        df_groups=df,
        df_countries=co2_int,
        selected_labels=series_selector,
        metric=metric_selector,
    )

    heading = pn.pane.Markdown(
        """
### 2. Emission intensity

Top panel: emission intensity over time (choose groups/countries and metric above).  
Bottom panel: indexed intensity (first non-zero year = 1) so you can compare **relative growth**.

**Reflection – emission intensity**

- CO₂ per capita shows that **Top-10 maritime economies** have long had higher emissions per person, but many now plateau or decline, while **Bottom-10 economies** rise as they industrialise and connect to seaborne trade.  
- CO₂ per unit of GDP highlights **structural efficiency**: some groups emit more for each unit of economic output, indicating more carbon-intensive energy or transport systems.  
- The indexed intensity view helps reveal **convergence or divergence** in carbon efficiency over time, beyond simple level comparisons.
        """,
        sizing_mode="stretch_width",
    )

    codes = pn.pane.Markdown(
        "**Intensity metric codes:** `per_capita` = t/person, "
        "`per_100k` = t per 100 000 people, `per_gdp` = t per unit GDP."
    )

    return pn.Column(
        heading,
        pn.Row(series_selector, metric_selector),
        intensity_plot,
        codes,
        intensity_index_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )



def create_section_ratio(df: pd.DataFrame):
    ratio_plot = make_ratio_plot(df)

    text = pn.pane.Markdown(
        """
### 3. Top / Bottom CO₂ ratio

How many times higher are emissions in the Top 10 group compared to the Bottom 10 group?  
Values above 1 mean Top 10 emits more.

**Reflection – Top/Bottom CO₂ ratio**

- In early years the ratio is extremely high because **Bottom-10 emissions are close to zero**, which compresses variation in later decades.  
- From the mid-20th century onwards the ratio falls and stabilises closer to a **single-digit multiple**, indicating that the gap between high- and low-maritime economies has narrowed substantially.  
- This single indicator summarises historical imbalance and provides a compact way to discuss **convergence**, while reminding us that modern-day levels remain very unequal.
        """,
        sizing_mode="stretch_width",
    )

    return pn.Column(
        text,
        ratio_plot,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )



def create_forecast_section(df: pd.DataFrame):

    targets = list(FORECAST_SERIES_MAP.keys())

    target_select = pn.widgets.Select(
        name="Forecast for",
        options=targets,
        value=targets[0],
        width=260,
    )

    def _forecast_view(target_label: str):
        forecast_plot, mae_naive, mae_lin = make_forecast_plot(df, target_label)

        info = pn.pane.Markdown(
            f"""
### 4. Short-term forecast for {target_label} CO₂  

We fit two simple models to **{target_label}** total CO₂ emissions
(from 1960 onwards) and forecast the next **3 years**:

- **Naive model:** extends the last observed value forward.  
- **Linear trend model:** fits a straight line to recent decades and extrapolates.

Backtesting on the last 3 observed years gives:

- Mean absolute error (MAE), naive model: **{mae_naive:,.1f} Mt**  
- Mean absolute error (MAE), linear model: **{mae_lin:,.1f} Mt**

**Reflection – forecasting and uncertainty**

- The **naive model** is conservative: it assumes emissions stay near the latest observed level and can work well when recent fluctuations are mostly noise.  
- The **linear trend model** extrapolates recent growth; it often predicts stronger increases but is more sensitive to the chosen time window.  
- Comparing the two highlights that even very simple time-series choices produce different futures, underlining the **uncertainty** in short-term maritime CO₂ projections.
""",
            sizing_mode="stretch_width",
        )

        return pn.Column(info, forecast_plot)

    dynamic_forecast = pn.bind(_forecast_view, target_label=target_select)

    return pn.Column(
        pn.Row(target_select),
        dynamic_forecast,
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

