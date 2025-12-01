# src/dashboard/controllers/shipping_controller.py
import panel as pn

from .maritime_section import create_maritime_group_section
from ..data.owid_groups import build_group_timeseries
from ..ui.storyboard_view import ShippingStoryboardView


class ShippingDashboardController:
    """
    Controller for the shipping/CO₂ storyboard dashboard.
    Loads data, constructs the view and exposes a root layout for app.py.
    """

    def __init__(self):
        # Henter aggregert CO₂-data + Top/Bottom ISO-grupper
        df, top_iso, bottom_iso = build_group_timeseries()

        print("AGG DATA SHAPE:", df.shape)
        print(df.head())
        print("Top ISO:", top_iso)
        print("Bottom ISO:", bottom_iso)

        # Hoved-storyboardet (OWID CO₂-story)
        self.view = ShippingStoryboardView(
            data=df,
            top_iso=top_iso,
            bottom_iso=bottom_iso,
        )

        # Ny seksjon: bruker SAMME top_iso / bottom_iso for porttrafikk + CO₂
        maritime_section = create_maritime_group_section(
            top_iso=top_iso,
            bottom_iso=bottom_iso,
        )

        # Ta hoved-layouten fra view og legg maritime-seksjonen nederst,
        # slik at den får samme padding/bredde som de andre seksjonene.
        root_layout = self.view.layout
        root_layout.append(maritime_section)

        self._layout = root_layout

    @property
    def layout(self):
        """
        Root layout brukt av app.py.
        Består av storyboardet + maritime-seksjonen nederst.
        """
        return self._layout
