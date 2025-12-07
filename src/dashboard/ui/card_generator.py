from __future__ import annotations

from pathlib import Path
from functools import lru_cache
import panel as pn
import pandas as pd

from .plot_generator import (
    make_total_co2_index_multi_plot,
    make_ratio_plot,
    make_forecast_plot,
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
    df = pd.read_csv(
        CO2_PATH,
        usecols=["country", "year", "co2", "cement_co2", "coal_co2"],
    )
    df = df.dropna(subset=["year"])
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
# How can we fight greenhouse emissions in maritime economies?

Global CO₂ emissions are still rising, but not all countries contribute – or improve – in the same way.  
This project asks: **how can maritime economies reduce greenhouse emissions while their ports keep growing?**

We combine OWID CO₂ data, container port traffic and a new maritime intensity classification to explore:

- Which countries **decouple** port growth from CO₂ (ports up while emissions stabilise or fall).  
- How emissions differ between **high-maritime and low-maritime economies**, using Top-10 and Bottom-10 groups.  
- Which structural factors – energy mix, sector composition and CO₂ efficiency per TEU – are linked to lower emissions.  

For the overview sections we build two data-driven comparison groups:

- **Top-10 maritime economies** – the 10 countries with the highest average container port traffic (TEU) between 2000 and the latest year in our dataset.  
- **Bottom-10 coastal economies** – 10 coastal countries with non-zero port traffic near the lower end of the same distribution.  

These groups are computed from our dataset (not an official OECD or IMO ranking) and are reused across the overview graphs and detailed maritime tabs.
        """,
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )



def create_key_messages():
    return pn.pane.HTML(
        """
<div class="key-messages">

  <div class="key-message-card">
    <h3>Why this dashboard?</h3>
    <p>
      Global CO₂ keeps increasing, but countries do not contribute equally.
      Here we compare <strong>Top-10 maritime economies</strong> with a
      <strong>Bottom-10 coastal group</strong> to see how strongly
      emissions are tied to container port activity and how this link evolves over time.
    </p>
  </div>

  <div class="key-message-card">
    <h3>1. Total CO₂ over time – setting the stage</h3>
    <p>
      The first graphs show absolute and indexed <strong>total CO₂</strong> for both groups.
      Top-10 maritime economies dominate global emissions in level terms, while the
      Bottom-10 group shows much faster <strong>relative growth</strong>, especially after 1950.
      This frames the basic scale and dynamics of the problem before we look at efficiency
      and the link to port traffic.
    </p>
  </div>

  <div class="key-message-card">
    <h3>2. Emission intensity – how carbon-heavy is growth?</h3>
    <p>
      We then move from totals to <strong>intensity</strong>:
      emissions per person, per 100&nbsp;000 people, or per unit of GDP.
      This reveals whether economies are becoming more
      <strong>carbon-efficient</strong> over time, and whether maritime leaders are
      converging towards cleaner growth compared to late-industrialising coastal states.
    </p>
  </div>

  <div class="key-message-card">
    <h3>3. Top/Bottom ratio – summarising the gap</h3>
    <p>
      A single ratio traces how many times higher Top-10 emissions are than those of
      the Bottom-10 group. It shows the huge historical imbalance and how the gap
      narrows as coastal latecomers industrialise, preparing the ground for questions
      about fairness and responsibility in maritime decarbonisation.
    </p>
  </div>

  <div class="key-message-card">
    <h3>4. Forecasts – where might we be heading?</h3>
    <p>
      Simple time-series models project short-term futures for the maritime groups.
      Comparing naive and linear-trend forecasts highlights both the momentum in
      emissions and the uncertainty involved, setting up the discussion of how
      strongly future CO₂ paths depend on shipping and trade policy choices.
    </p>
  </div>

</div>
        """,
        sizing_mode="stretch_width",
    )
def create_next_tabs_card() -> pn.Column:
    """
    Overview card that explains what the other dashboard tabs do.
    """
    text = pn.pane.Markdown(
        """
### Explnation of the next tabs

After this overview you can dive into several more tabs that provide tools for further analysis:

2. **Decoupling explorer**  
   Classify countries into **strong decouplers, weak decouplers and “brown growth”**
   based on how port traffic and CO₂ have grown since 2000, and use timelines to see
   when a country starts (or stops) decoupling.
   
3. **Success factors**  
   Explore which structural variables (energy per GDP, fuel mix, etc.) correlate most
   strongly with **low CO₂ per TEU**, and inspect simple regression lines for potential
   “levers” behind maritime decarbonisation.
   
4. **Peer benchmarking**  
   Pick a country and compare it with **similar peers** in terms of GDP and port size,
   using a compact table and narrative summary to highlight who is already doing better
   at keeping CO₂ per TEU down.

5. **Efficiency frontier**  
   For a chosen year, plot CO₂ per TEU against port traffic and draw a simple
   **“best-practice” frontier**. Countries close to the line are efficient; those far
   above it have room to improve maritime carbon efficiency.
   
6. **Sectoral breakdown**  
   Decompose CO₂ into **power, industry, transport, buildings, etc.** for different
   maritime tiers, and see how big a share of total emissions comes from explicitly
   **maritime-related CO₂** in the latest year.

Together with the **2030 scenario tool** at the end, these tabs let you go from
high-level group comparisons to detailed, country-by-country stories about how
maritime trade and CO₂ emissions are linked – and how that link might be weakened.
        """,
        sizing_mode="stretch_width",
    )

    return pn.Column(text, sizing_mode="stretch_width", css_classes=["story-step-card"])


def create_controls_row(intensity_widget: pn.widgets.Select):
    return pn.Row(sizing_mode="stretch_width")


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

    secondary_metric_select = pn.widgets.Select(
        name="Additional emission variable (right axis)",
        options={
            "None": "none",
            "Cement CO₂": "cement_co2",
            "Coal CO₂": "coal_co2",
        },
        value="none",
        width=280,
    )

    total_dual_axis_plot = pn.bind(
        make_total_co2_multi_plot,
        df_groups=df,
        df_countries=co2_all,
        selected_labels=series_selector,
        secondary_metric=secondary_metric_select,
    )

    total_index_plot = pn.bind(
        make_total_co2_index_multi_plot,
        df_groups=df,
        df_countries=co2_all,
        selected_labels=series_selector,
        secondary_metric=secondary_metric_select,
    )

    intro = pn.pane.Markdown(
        """
### 1. Total CO₂ over time

The first step is to look at **total CO₂ emissions** for our two reference groups
(Top-10 maritime and Bottom-10 coastal) and any extra countries you add.

- The **top panel** shows emissions in absolute terms. Here you can see how
  leading maritime economies dominate global CO₂, while low-emitting coastal
  countries contribute only a small share.  
- The **bottom panel** uses an indexed scale (first non-zero year = 1), which
  makes it easier to compare **relative growth**. In this view the Bottom-10 line
  often climbs much faster, highlighting that late-industrialising coastal
  economies are now among the fastest-growing emitters.  
- This card sets the overall **scale and trajectory** of emissions before we
  move on to ask how carbon-intensive that growth is and how it connects to
  maritime trade.
        """,
        sizing_mode="stretch_width",
    )

    return pn.Column(
        intro,
        pn.Row(series_selector, secondary_metric_select),
        total_dual_axis_plot,
        pn.pane.Markdown("_Indexed growth (first non-zero = 1)_"),
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

Here we switch from total tonnes to **emission intensity** – how much CO₂ is
emitted per person, per 100 000 people, or per unit of GDP.

- The **top panel** shows the level of intensity. It reveals that
  **Top-10 maritime economies** have long had much higher CO₂ per capita, but
  many now **peak and decline**, while **Bottom-10 economies** rise as they
  industrialise and connect to seaborne trade.  
- CO₂ per unit of GDP highlights **structural efficiency**: some groups emit
  more for each unit of economic output, indicating more carbon-intensive
  energy or transport systems.  
- The **indexed intensity** view below focuses on **relative change**. A flat
  or declining line means that a group is becoming more carbon-efficient over
  time, even if its total emissions are still high. This links directly to our
  question of whether maritime economies are managing to grow trade without
  growing emissions as fast.
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

This card compresses the comparison into a **single time series**:  
how many times higher are emissions in the Top-10 maritime group than in the
Bottom-10 coastal group?

- In early years the ratio is extremely high because **Bottom-10 emissions are
  close to zero**, which makes the Top-10 look infinitely larger.  
- From the mid-20th century onwards the ratio falls and stabilises around a
  **single-digit multiple**, showing that the gap between high- and low-maritime
  economies has narrowed substantially as coastal latecomers industrialise.  
- This simple indicator summarises the historical imbalance in maritime-linked
  emissions and prepares the ground for later sections where we ask whether the
  remaining gap is justified by differences in trade intensity and port activity.
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

To close the overview we look briefly into the **near future**.  
We fit two simple models to **{target_label}** total CO₂ emissions (from 1960 onwards)
and forecast the next **3 years**:

- **Naive model:** extends the last observed value forward.  
- **Linear trend model:** fits a straight line to recent decades and extrapolates.

Backtesting on the last 3 observed years gives:

- Mean absolute error (MAE), naive model: **{mae_naive:,.1f} Mt**  
- Mean absolute error (MAE), linear model: **{mae_lin:,.1f} Mt**

**Reflection – forecasting and uncertainty**

- The **naive model** is conservative: it assumes emissions stay near the latest
  observed level and can work well when recent fluctuations are mostly noise.  
- The **linear trend model** extrapolates recent growth; it often predicts
  stronger increases but is more sensitive to the chosen time window.  
- Comparing the two highlights that even very simple time-series choices produce
  different futures, underlining the **uncertainty** in short-term maritime
  CO₂ projections and motivating the deeper sector and port-traffic analysis in
  the rest of the dashboard.
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