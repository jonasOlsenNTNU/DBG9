# src/dashboard/app.py
from __future__ import annotations

import argparse

import panel as pn

from src.utils.data import load_analysis_dataset, rebuild_analysis_dataset
from src.dashboard.controllers.shipping_controller import ShippingDashboardController
from src.dashboard.ui.decoupling_view import create_decoupling_tab
from src.dashboard.ui.factor_analysis_view import create_success_factors_tab
from src.dashboard.ui.benchmarking_view import create_benchmarking_tab
from src.dashboard.ui.frontier_view import create_frontier_tab
from src.dashboard.ui.sectoral_view import create_sectoral_tab
from src.dashboard.ui.scenario_tool import create_scenario_tab
from src.dashboard.utils.load_css import load_css


pn.extension("tabulator")

# Load CSS files
load_css("tab_navigation.css")


def make_dashboard() -> pn.Tabs:
    # Load analysis-ready dataset (Phase 1 output)
    df = load_analysis_dataset()

    # Overview: reuse your existing storyboard + maritime sections
    controller = ShippingDashboardController()
    overview_layout = controller.layout

    decoupling_tab = create_decoupling_tab(df)
    success_tab = create_success_factors_tab(df)
    benchmarking_tab = create_benchmarking_tab(df)
    frontier_tab = create_frontier_tab(df)
    sectoral_tab = create_sectoral_tab(df)
    scenario_tab = create_scenario_tab(df)

    tabs = pn.Tabs(
        ("1. Overview", overview_layout),
        ("2. Decoupling explorer", decoupling_tab),
        ("3. Success factors", success_tab),
        ("4. Peer benchmarking", benchmarking_tab),
        ("5. Efficiency frontier", frontier_tab),
        ("6. Sectoral breakdown", sectoral_tab),
        ("7. Scenario modelling", scenario_tab),
    )

    # Important: only stretch horizontally, let each tab decide its height from the plots
    tabs.sizing_mode = "stretch_width"

    return tabs



def main(rebuild_dataset: bool = False):
    if rebuild_dataset:
        rebuild_analysis_dataset()
    dashboard = make_dashboard()
    return dashboard


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rebuild-dataset",
        action="store_true",
        help="Rebuild analysis_ready.csv before starting the dashboard.",
    )
    args = parser.parse_args()

    app = main(rebuild_dataset=args.rebuild_dataset)
    pn.serve(
        app,
        title="Maritime Emissions Analysis Dashboard",
        show=True,
    )
