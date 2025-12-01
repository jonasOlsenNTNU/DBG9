from .maritime_section import create_maritime_group_section
from ..data.owid_groups import build_group_timeseries
from ..ui.storyboard_view import ShippingStoryboardView


class ShippingDashboardController:

    def __init__(self):
        df, top_iso, bottom_iso = build_group_timeseries()

        print("AGG DATA SHAPE:", df.shape)
        print(df.head())
        print("Top ISO:", top_iso)
        print("Bottom ISO:", bottom_iso)

        self.view = ShippingStoryboardView(
            data=df,
            top_iso=top_iso,
            bottom_iso=bottom_iso,
        )

        maritime_section = create_maritime_group_section(
            top_iso=top_iso,
            bottom_iso=bottom_iso,
        )

        root_layout = self.view.layout
        root_layout.append(maritime_section)

        self._layout = root_layout

    @property
    def layout(self):
        return self._layout
