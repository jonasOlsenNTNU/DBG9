from __future__ import annotations

import numpy as np
import pandas as pd
import panel as pn

TOP_COLOR = "#004c6d"
BOTTOM_COLOR = "#2a9d8f"
FORECAST_MAIN_COLOR = "#e76f51"
FORECAST_NAIVE_COLOR = "#f4a261"

FORECAST_SERIES_MAP = {
    "Top 10 maritime (avg)": ("co2_top10", "Top 10 total CO₂ (Mt)"),
    "Bottom 10 coastal (avg)": ("co2_bottom10", "Bottom 10 total CO₂ (Mt)"),
}



def _total_series_for_label(
        df_groups: pd.DataFrame,
        df_countries: pd.DataFrame,
        label: str,
):
    if label == "Top 10 maritime (avg)":
        series_df = (
            df_groups[["year", "co2_top10"]]
            .rename(columns={"co2_top10": "co2"})
            .copy()
        )
        color = TOP_COLOR

    elif label == "Bottom 10 coastal (avg)":
        series_df = (
            df_groups[["year", "co2_bottom10"]]
            .rename(columns={"co2_bottom10": "co2"})
            .copy()
        )
        color = BOTTOM_COLOR

    else:
        series_df = df_countries[df_countries["country"] == label][
            ["year", "co2"]
        ].copy()
        color = None

    series_df = series_df.dropna(subset=["co2"])
    return series_df, color

def make_total_co2_multi_plot(
        df_groups: pd.DataFrame,
        df_countries: pd.DataFrame,
        selected_labels: list[str],
):
    if not selected_labels:
        return pn.pane.Markdown("⚠️ Select at least one group or country.")

    min_year = int(df_groups["year"].min())
    max_year = int(df_groups["year"].max())
    df_c = df_countries[
        (df_countries["year"] >= min_year) & (df_countries["year"] <= max_year)
        ]

    curves = []
    for label in selected_labels:
        series_df, color = _total_series_for_label(df_groups, df_c, label)
        if series_df.empty:
            continue

        kwargs = dict(
            x="year",
            y="co2",
            label=label,
            line_width=2,
        )
        if color is not None:
            kwargs["color"] = color

        curves.append(series_df.hvplot.line(**kwargs))

    if not curves:
        return pn.pane.Markdown(
            "⚠️ No total CO₂ data for the current selection."
        )

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
        legend_position="top_left",
        xlim=(min_year, max_year),
    )




def make_total_co2_index_multi_plot(
        df_groups: pd.DataFrame,
        df_countries: pd.DataFrame,
        selected_labels: list[str],
):

    if not selected_labels:
        return pn.pane.Markdown("⚠️ Select at least one group or country.")

    min_year = int(df_groups["year"].min())
    max_year = int(df_groups["year"].max())
    df_c = df_countries[
        (df_countries["year"] >= min_year) & (df_countries["year"] <= max_year)
        ]

    curves = []
    for label in selected_labels:
        series_df, color = _total_series_for_label(df_groups, df_c, label)
        if series_df.empty:
            continue

        non_zero = series_df.loc[series_df["co2"] > 0, "co2"]
        if non_zero.empty:
            continue
        base = non_zero.iloc[0]

        idx_df = series_df.copy()
        idx_df["index"] = idx_df["co2"] / base

        kwargs = dict(
            x="year",
            y="index",
            label=label,
            line_width=2,
        )
        if color is not None:
            kwargs["color"] = color

        curves.append(idx_df.hvplot.line(**kwargs))

    if not curves:
        return pn.pane.Markdown(
            "⚠️ No data to compute indexed growth for this selection."
        )

    plot = curves[0]
    for c in curves[1:]:
        plot = plot * c

    return plot.opts(
        xlabel="Year",
        ylabel="Indexed total CO₂ (first non-zero = 1)",
        height=380,
        show_grid=True,
        toolbar=None,
        legend_position="top_left",
        xlim=(min_year, max_year),
    )





def make_total_co2_log_plot(df: pd.DataFrame):
    log_df = df[df["year"] >= 1960][["year", "co2_top10", "co2_bottom10"]].copy()

    plot = log_df.hvplot.line(
        x="year",
        y=["co2_top10", "co2_bottom10"],
        value_label="Total CO₂ (Mt, log scale)",
        logy=True,
        line_width=2,
        legend="top_left",
        color=[TOP_COLOR, BOTTOM_COLOR],
        label="",
    )

    return plot.opts(
        xlabel="Year",
        ylabel="Total CO₂ (Mt, log scale)",
        height=320,
        show_grid=True,
        toolbar=None,
    )


def make_total_co2_share_area(df):
    area_df = df[df["year"] >= 1960][["year","co2_top10","co2_bottom10"]].copy()
    area_df = area_df.melt(id_vars="year", value_vars=["co2_top10","co2_bottom10"],
                           var_name="group", value_name="co2")
    area_df["total"] = area_df.groupby("year")["co2"].transform("sum")
    area_df["share"] = 100 * area_df["co2"] / area_df["total"]

    label_map = {
        "co2_top10": "Top 10 – share of total",
        "co2_bottom10": "Bottom 10 – share of total",
    }
    area_df["label"] = area_df["group"].map(label_map)

    return area_df.hvplot.area(
        x="year", y="share", by="label", stacked=True,
    ).opts(ylabel="Share of total CO₂ (%)", ylim=(0, 100))



def make_ratio_plot(df: pd.DataFrame):
    ratio_plot = df.hvplot.line(
        x="year",
        y="co2_ratio_top_over_bottom",
        label="Top / Bottom total CO₂",
        line_width=2,
        color=TOP_COLOR,
        xlim=(1858,2024)
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
def _intensity_series_for_label(
        df_groups: pd.DataFrame,
        df_countries: pd.DataFrame,
        label: str,
        metric: str,
):
    if label == "Top 10 maritime (avg)":
        if metric in ("per_capita", "per_100k"):
            col = "co2pc_top10"
        elif metric == "per_gdp":
            col = "co2gdp_top10"
        else:
            raise ValueError(f"Unknown metric: {metric}")
        series_df = df_groups[["year", col]].rename(columns={col: "value"}).copy()
        if metric == "per_100k":
            series_df["value"] = series_df["value"] * 1e5
        color = TOP_COLOR

    elif label == "Bottom 10 coastal (avg)":
        if metric in ("per_capita", "per_100k"):
            col = "co2pc_bottom10"
        elif metric == "per_gdp":
            col = "co2gdp_bottom10"
        else:
            raise ValueError(f"Unknown metric: {metric}")
        series_df = df_groups[["year", col]].rename(columns={col: "value"}).copy()
        if metric == "per_100k":
            series_df["value"] = series_df["value"] * 1e5
        color = BOTTOM_COLOR

    else:
        sub = df_countries[df_countries["country"] == label].copy()
        if sub.empty:
            return None, None

        if metric == "per_capita":
            if "co2_per_capita" in sub.columns:
                sub["value"] = sub["co2_per_capita"]
            elif {"co2", "population"} <= set(sub.columns):
                sub["value"] = sub["co2"] / sub["population"]
            else:
                return None, None

        elif metric == "per_100k":
            if "co2_per_capita" in sub.columns:
                sub["value"] = sub["co2_per_capita"] * 1e5
            elif {"co2", "population"} <= set(sub.columns):
                sub["value"] = sub["co2"] * 1e5 / sub["population"]
            else:
                return None, None

        elif metric == "per_gdp":
            if "co2_per_gdp" in sub.columns:
                sub["value"] = sub["co2_per_gdp"]
            elif {"co2", "gdp"} <= set(sub.columns):
                sub["value"] = sub["co2"] / sub["gdp"]
            else:
                return None, None

        else:
            return None, None

        series_df = sub[["year", "value"]].dropna().copy()
        color = None

    series_df = series_df.dropna(subset=["value"])
    return series_df, color

def make_intensity_multi_plot(
        df_groups: pd.DataFrame,
        df_countries: pd.DataFrame,
        selected_labels: list[str],
        metric: str,
):
    if metric is None:
        metric = "per_capita"

    if not selected_labels:
        return pn.pane.Markdown("⚠️ Select at least one group or country.")

    series_list: list[tuple[str, pd.DataFrame, str | None]] = []
    for label in selected_labels:
        series_df, color = _intensity_series_for_label(
            df_groups, df_countries, label, metric
        )
        if series_df is None or series_df.empty:
            continue
        series_list.append((label, series_df, color))

    if not series_list:
        return pn.pane.Markdown(
            f"⚠️ No intensity data for metric `{metric}` and current selection."
        )

    years = np.concatenate([s["year"].values for _, s, _ in series_list])
    vals  = np.concatenate([s["value"].values for _, s, _ in series_list])

    mask = np.isfinite(years) & np.isfinite(vals)
    years, vals = years[mask], vals[mask]

    if vals.size == 0:
        return pn.pane.Markdown(
            f"⚠️ No finite intensity values for metric `{metric}`."
        )

    min_year = int(years.min())
    max_year = int(years.max())

    y_min = float(vals.min())
    y_max = float(vals.max())

    if y_min == y_max:
        if y_min == 0:
            y_min, y_max = 0.0, 1.0
        else:
            y_min *= 0.9
            y_max *= 1.1

    if y_min > 0:
        y_min = 0.0

    margin = 0.05 * (y_max - y_min)
    low = y_min - margin
    high = y_max + margin

    if metric == "per_capita":
        ylabel = "CO₂ per capita (t/person)"
    elif metric == "per_100k":
        ylabel = "CO₂ per 100 000 people (t per 100k)"
    elif metric == "per_gdp":
        ylabel = "CO₂ per unit GDP (t per unit GDP)"
    else:
        ylabel = "Emission intensity"

    curves = []
    for label, series_df, color in series_list:
        series_df = series_df[
            (series_df["year"] >= min_year) & (series_df["year"] <= max_year)
            ]
        if series_df.empty:
            continue

        kwargs = dict(
            x="year",
            y="value",
            label=label,
            line_width=2,
        )
        if color is not None:
            kwargs["color"] = color

        curves.append(series_df.hvplot.line(**kwargs))

    if not curves:
        return pn.pane.Markdown(
            f"⚠️ No finite intensity values for metric `{metric}`."
        )

    plot = curves[0]
    for c in curves[1:]:
        plot = plot * c

    return plot.opts(
        xlabel="Year",
        ylabel=ylabel,
        height=340,
        show_grid=True,
        toolbar=None,
        legend_position="top_left",
        xlim=(min_year, max_year),
        ylim=(low, high),
        shared_axes=False,
        framewise=True,
    )



def make_intensity_index_multi_plot(
        df_groups: pd.DataFrame,
        df_countries: pd.DataFrame,
        selected_labels: list[str],
        metric: str,
):
    if metric is None:
        metric = "per_capita"
        print("There is no metric" + metric)
    if not selected_labels:
            return None


    min_year = int(df_groups["year"].min())
    max_year = int(df_groups["year"].max())
    df_c = df_countries[
        (df_countries["year"] >= min_year) & (df_countries["year"] <= max_year)
        ]

    curves = []
    for label in selected_labels:
        series_df, color = _intensity_series_for_label(df_groups, df_c, label, metric)
        if series_df is None or series_df.empty:
            continue

        non_zero = series_df.loc[series_df["value"] > 0, "value"]
        base = non_zero.iloc[0] if not non_zero.empty else series_df["value"].iloc[0]
        if base == 0 or np.isnan(base):
            continue

        idx_df = series_df.copy()
        idx_df["index"] = idx_df["value"] / base

        kwargs = dict(
            x="year",
            y="index",
            label=label,
            line_width=2,
        )
        if color is not None:
            kwargs["color"] = color

        curves.append(idx_df.hvplot.line(**kwargs))

        if not curves:
            return pn.pane.Markdown(
                f"⚠️ Cannot compute indexed intensity for metric `{metric}` "
                "and current selection (no non-zero data)."
            )

    plot = curves[0]
    for c in curves[1:]:
        plot = plot * c


    plot = curves[0]
    for c in curves[1:]:
        plot = plot * c

    return plot.opts(
        xlabel="Year",
        ylabel="Indexed intensity (first non-zero = 1)",
        height=380,
        show_grid=True,
        toolbar=None,
        legend_position="top_left",
    )



def make_forecast_plot(df: pd.DataFrame, target: str = "Top 10 maritime (avg)"):
    col, ylabel = FORECAST_SERIES_MAP.get(
        target, ("co2_top10", f"{target} total CO₂ (Mt)")
    )

    df_recent = df[df["year"] >= 1960].copy()
    years = df_recent["year"].values.astype(float)
    y = df_recent[col].values

    last_year = int(df_recent["year"].max())
    horizon = 3

    future_years = np.arange(last_year + 1, last_year + 1 + horizon)

    naive_future = np.full(horizon, y[-1])

    coef = np.polyfit(years, y, 1)
    lin_model = np.poly1d(coef)
    linear_future = lin_model(future_years)

    cut_year = last_year - horizon
    train_mask = df_recent["year"] <= cut_year
    test_mask = df_recent["year"] > cut_year

    train_years = df_recent.loc[train_mask, "year"].values.astype(float)
    train_y = df_recent.loc[train_mask, col].values
    test_years = df_recent.loc[test_mask, "year"].values.astype(float)
    test_y = df_recent.loc[test_mask, col].values

    coef_bt = np.polyfit(train_years, train_y, 1)
    lin_bt = np.poly1d(coef_bt)(test_years)
    naive_bt = np.full_like(test_y, train_y[-1])

    mae_lin = float(np.mean(np.abs(test_y - lin_bt)))
    mae_naive = float(np.mean(np.abs(test_y - naive_bt)))

    hist_years = df_recent["year"].values
    hist_vals = df_recent[col].values

    plot_df = pd.DataFrame(
        {
            "year": np.concatenate([hist_years, future_years, future_years]),
            "value": np.concatenate([hist_vals, linear_future, naive_future]),
            "series": (
                    ["History"] * len(hist_years)
                    + ["Linear forecast"] * len(future_years)
                    + ["Naive forecast"] * len(future_years)
            ),
        }
    )

    min_year_plot = max(int(hist_years.min()), last_year - 35)
    max_year_plot = last_year + horizon

    color_key = {
        "History": TOP_COLOR,
        "Linear forecast": FORECAST_MAIN_COLOR,
        "Naive forecast": FORECAST_NAIVE_COLOR,
    }

    forecast_plot = plot_df.hvplot.line(
        x="year",
        y="value",
        by="series",
        line_width=3,
        color_key=color_key,
    ).opts(
        xlabel="Year",
        ylabel=ylabel,
        height=340,
        show_grid=True,
        toolbar=None,
        legend_position="top_left",
        xlim=(min_year_plot, max_year_plot),
    )

    return forecast_plot, mae_naive, mae_lin
