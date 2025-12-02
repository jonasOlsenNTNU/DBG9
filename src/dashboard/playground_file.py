from __future__ import annotations

import numpy as np


from .data.owid_groups import build_group_timeseries
from .ui.card_generator import _load_owid_co2_for_intensity
from .ui.plot_generator import _intensity_series_for_label


def debug_intensity(selected_labels, metric: str = "per_capita"):

    print(f"\n=== DEBUG INTENSITY for metric = {metric} ===")

    df_groups, top_iso, bottom_iso = build_group_timeseries()
    co2_int = _load_owid_co2_for_intensity()

    series_list = []

    for label in selected_labels:
        series_df, _ = _intensity_series_for_label(df_groups, co2_int, label, metric)
        if series_df is None or series_df.empty:
            print(f"- {label}: NO DATA")
            continue

        vals = series_df["value"].to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]

        if vals.size == 0:
            print(f"- {label}: only non-finite values")
            continue

        print(
            f"- {label}: "
            f"min={vals.min():.4g}, "
            f"max={vals.max():.4g}, "
            f"q1={np.quantile(vals, 0.25):.4g}, "
            f"median={np.quantile(vals, 0.5):.4g}, "
            f"q3={np.quantile(vals, 0.75):.4g}"
        )

        series_list.append(vals)

    if not series_list:
        print(">>> No usable series.")
        return

    all_vals = np.concatenate(series_list)
    all_vals = all_vals[np.isfinite(all_vals)]

    print("\n>>> GLOBAL over selected series:")
    print(f"    min  = {all_vals.min():.4g}")
    print(f"    max  = {all_vals.max():.4g}")
    print(f"    q1   = {np.quantile(all_vals, 0.25):.4g}")
    print(f"    q50  = {np.quantile(all_vals, 0.50):.4g}")
    print(f"    q75  = {np.quantile(all_vals, 0.75):.4g}")
    print(f"    q99  = {np.quantile(all_vals, 0.99):.4g}")

    y_min = float(all_vals.min())
    y_max = float(all_vals.max())
    if y_min > 0:
        y_min = 0.0
    margin = 0.05 * (y_max - y_min)
    low = y_min - margin
    high = y_max + margin
    print(f"\n>>> Suggested ylim would be: ({low:.4g}, {high:.4g})")


def main():
    labels = ["Top 10 maritime (avg)", "Bottom 10 coastal (avg)"]
    debug_intensity(labels, metric="per_capita")
    debug_intensity(labels, metric="per_gdp")


if __name__ == "__main__":
    main()
