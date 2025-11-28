# src/dashboard/controllers/shipping_controller.py
import panel as pn

from ..data.owid_groups import build_group_timeseries
from ..ui.storyboard_view import ShippingStoryboardView


class ShippingDashboardController:
    """
    Controller for the shipping/CO₂ storyboard dashboard.
    Loads data and passes it to the view.
    """

    def __init__(self):
        df, top_iso, bottom_iso = build_group_timeseries()

        print("AGG DATA SHAPE:", df.shape)
        print(df.head())
        print("Top ISO:", top_iso)
        print("Bottom ISO:", bottom_iso)

        self.view = ShippingStoryboardView(data=df, top_iso=top_iso, bottom_iso=bottom_iso)

    def layout(self) -> pn.layout.Panel:
        """Entry point for pn.serve"""
        return self.view.view()
