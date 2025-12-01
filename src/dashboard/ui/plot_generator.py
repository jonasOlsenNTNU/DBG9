from __future__ import annotations

import numpy as np
import pandas as pd
import hvplot.pandas


TOP_COLOR = "#004c6d"
BOTTOM_COLOR = "#2a9d8f"


def make_total_co2_plot(df: pd.DataFrame):
    curves = [
        df.hvplot.line(
            x="year",
            y="co2_top10",
            label="Top 10 – total CO₂",
            line_width=2,
            color=TOP_COLOR,
        ),
        df.hvplot.line(
            x="year",
            y="co2_bottom10",
            label="Bottom 10 – total CO₂",
            line_width=2,
            line_dash="dotted",
            color=BOTTOM_COLOR,
        ),
    ]

    plot = curves[0]
    for c in curves[1:]:
        plot = plot * c

    return plot.opts(
        xlabel="Year",
        ylabel="Total CO₂ (Mt, avg per country)",
        height=320,
        show_grid=True,
        toolbar=None,
        shared_axes=False,
        framewise=True,
    )


def make_total_co2_index_plot(df: pd.DataFrame):
    curves = [
        df.hvplot.line(
            x="year",
            y="co2_top10_index",
            label="Top 10 – indexed CO₂",
            line_width=2,
            color=TOP_COLOR,
        ),
        df.hvplot.line(
            x="year",
            y="co2_bottom10_index",
            label="Bottom 10 – indexed CO₂",
            line_width=2,
            line_dash="dotted",
            color=BOTTOM_COLOR,
        ),
    ]

    plot = curves[0]
    for c in curves[1:]:
        plot = plot * c

    return plot.opts(
        xlabel="Year",
        ylabel="Index (first year = 1)",
        height=320,
        show_grid=True,
        toolbar=None,
        shared_axes=False,
        framewise=True,
    )


def make_intensity_plot(df: pd.DataFrame, metric: str):
    if metric == "per_gdp":
        y_top, y_bottom = "co2gdp_top10", "co2gdp_bottom10"
        ylabel = "CO₂ per GDP (t per unit GDP)"
        label_suffix = " per GDP"
    else:
        y_top, y_bottom = "co2pc_top10", "co2pc_bottom10"
        ylabel = "CO₂ per capita (t/person)"
        label_suffix = " per capita"

    curves = [
        df.hvplot.line(
            x="year",
            y=y_top,
            label=f"Top 10{label_suffix}",
            line_width=2,
            color=TOP_COLOR,
        ),
        df.hvplot.line(
            x="year",
            y=y_bottom,
            label=f"Bottom 10{label_suffix}",
            line_width=2,
            line_dash="dotted",
            color=BOTTOM_COLOR,
        ),
    ]

    plot = curves[0]
    for c in curves[1:]:
        plot = plot * c

    return plot.opts(
        xlabel="Year",
        ylabel=ylabel,
        height=320,
        show_grid=True,
        toolbar=None,
        shared_axes=False,
        framewise=True,
    )


def make_ratio_plot(df: pd.DataFrame):
    ratio_plot = df.hvplot.line(
        x="year",
        y="co2_ratio_top_over_bottom",
        label="Top / Bottom total CO₂",
        line_width=2,
        color=TOP_COLOR,
    )

    return ratio_plot.opts(
        xlabel="Year",
        ylabel="Top / Bottom total CO₂ (ratio)",
        height=320,
        show_grid=True,
        toolbar=None,
        shared_axes=False,
        framewise=True,
    )


def make_forecast_plot(df: pd.DataFrame):

    df_recent = df[df["year"] >= 1960].copy()
    years = df_recent["year"].values.astype(float)
    y = df_recent["co2_top10"].values

    last_year = int(df_recent["year"].max())
    horizon = 10

    future_years = np.arange(last_year + 1, last_year + 1 + horizon)

    naive_future = np.full(horizon, y[-1])


    coef = np.polyfit(years, y, 1)
    lin_model = np.poly1d(coef)
    linear_future = lin_model(future_years)


    cut_year = last_year - horizon
    train_mask = df_recent["year"] <= cut_year
    test_mask = df_recent["year"] > cut_year

    train_years = df_recent.loc[train_mask, "year"].values.astype(float)
    train_y = df_recent.loc[train_mask, "co2_top10"].values
    test_years = df_recent.loc[test_mask, "year"].values.astype(float)
    test_y = df_recent.loc[test_mask, "co2_top10"].values


    coef_bt = np.polyfit(train_years, train_y, 1)
    lin_bt = np.poly1d(coef_bt)(test_years)
    naive_bt = np.full_like(test_y, train_y[-1])

    mae_lin = float(np.mean(np.abs(test_y - lin_bt)))
    mae_naive = float(np.mean(np.abs(test_y - naive_bt)))


    hist_recent = df_recent[df_recent["year"] >= 2000]
    hist_years = hist_recent["year"].values
    hist_vals = hist_recent["co2_top10"].values

    plot_df = pd.DataFrame(
        {
            "year": np.concatenate(
                [hist_years, future_years, future_years]
            ),
            "value": np.concatenate(
                [hist_vals, linear_future, naive_future]
            ),
            "series": (
                    ["History"] * len(hist_years)
                    + ["Linear forecast"] * len(future_years)
                    + ["Naive forecast"] * len(future_years)
            ),
        }
    )

    forecast_plot = plot_df.hvplot.line(
        x="year",
        y="value",
        by="series",
        line_width=2,
    ).opts(
        xlabel="Year",
        ylabel="Top 10 total CO₂ (Mt)",
        height=320,
        show_grid=True,
        toolbar=None,
        legend_position="top_left",
        xlim=(2000, last_year + horizon),
    )

    return forecast_plot, mae_naive, mae_lin
