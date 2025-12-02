from __future__ import annotations

import panel as pn

from ..utils.load_css import load_css
from .card_generator import (
    create_header,
    create_key_messages,
    create_controls_row,
    create_section_total,
    create_section_intensity,
    create_section_ratio,
    create_forecast_section,
)

pn.extension("tabulator")


class ShippingStoryboardView:

    def __init__(self, data, top_iso=None, bottom_iso=None):
        self.data = data
        self.top_iso = top_iso or []
        self.bottom_iso = bottom_iso or []

        load_css("main_view.css")

        self.intensity_metric_select = pn.widgets.Select(
            name="Intensity metric",
            options={
                "CO₂ per capita (t/person)": "per_capita",
                "CO₂ per GDP (t per unit GDP)": "per_gdp",
            },
            value="per_capita",
        )

        header = create_header()
        key_messages = create_key_messages()
        controls_row = create_controls_row(self.intensity_metric_select)

        section_total = create_section_total(self.data)
        section_intensity = create_section_intensity(self.data)
        section_ratio = create_section_ratio(self.data)
        self.forecast_section = create_forecast_section(self.data)

        self._layout = pn.Column(
            header,
            key_messages,
            controls_row,
            section_total,
            section_intensity,
            section_ratio,
            sizing_mode="stretch_both",
            css_classes=["story-layout"],
        )

    def view(self):
        return self._layout

    @property
    def layout(self):
        return self._layout

    def __panel__(self):

        return self._layout
