# src/dashboard/ui/scenario_tool.py
from __future__ import annotations

import panel as pn
import pandas as pd


def create_scenario_tab(df: pd.DataFrame) -> pn.Column:
    """
    Tab 7: Simple 2030 scenario tool (placeholder).
    """
    header = pn.pane.Markdown(
        """
# 2030 scenario modelling (prototype)

This section is reserved for a simple **2030 scenario tool** where you can
adjust **port growth** and **CO₂ intensity improvements** to see projected
emissions and efficiency.

The current version is a styled placeholder, ready for a later model.
        """,
        sizing_mode="stretch_width",
        css_classes=["story-header"],
    )

    placeholder_card = pn.Column(
        pn.pane.Markdown(
            "🛠️ Scenario engine not implemented yet.\n\n"
            "You can add sliders and a regression-based projection model here later.",
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
        css_classes=["story-step-card"],
    )

    return pn.Column(
        header,
        placeholder_card,
        sizing_mode="stretch_width",
        css_classes=["story-layout"],
    )

