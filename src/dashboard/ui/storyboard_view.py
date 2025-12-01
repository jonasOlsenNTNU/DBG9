from __future__ import annotations

import panel as pn
import hvplot.pandas  # noqa: F401

from ..utils.load_css import load_css

pn.extension("tabulator")


class ShippingStoryboardView:
    """
    Vertical layout for comparing Top 10 vs Bottom 10 maritime country groups
    using ONLY OWID CO₂ data.

    Sections:
      1) Total CO₂ over time (absolute + indexed)
      2) Emission intensity (per capita or per GDP)
      3) Ratio of Top 10 to Bottom 10 total CO₂
    """

    def __init__(self, data, top_iso=None, bottom_iso=None):
        self.data = data
        self.top_iso = top_iso or []
        self.bottom_iso = bottom_iso or []

        load_css("main_view.css")

        # --------- widgets ----------
        self.intensity_metric_select = pn.widgets.Select(
            name="Intensity metric",
            options={
                "CO₂ per capita (t/person)": "per_capita",
                "CO₂ per GDP (t per unit GDP)": "per_gdp",
            },
            value="per_capita",
        )

        # --------- plots (bindings) ----------
        total_abs_plot = self._total_co2_plot()
        total_index_plot = self._total_co2_index_plot()
        intensity_plot = pn.bind(
            self._intensity_plot, metric=self.intensity_metric_select
        )
        ratio_plot = self._ratio_plot()

        # --------- header ----------
        header = pn.pane.Markdown(
            """
# How do CO₂ emissions differ between highly maritime and low-maritime economies?

We split countries into two groups based on external shipping statistics:

- **Top 10 maritime economies** (large ports, strong shipping sector)
- **Bottom 10 coastal economies** with relatively low maritime activity

Using the OWID CO₂ dataset, this dashboard lets you:

- Compare **total CO₂ emissions** between the two groups over time.
- Explore **emission intensity** (per capita or per unit of GDP).
- Examine how the **ratio Top/Bottom** has changed – i.e. are maritime economies
  becoming relatively cleaner or dirtier over time?

_Later we can plug back in a dedicated shipping-emissions dataset to connect these
patterns more directly to shipping volumes._
            """,
            sizing_mode="stretch_width",
            css_classes=["story-header"],
        )

        controls_row = pn.Row(
            pn.pane.Markdown(
                "Intensity metric (section 2):", sizing_mode="fixed"
            ),
            self.intensity_metric_select,
            sizing_mode="stretch_width",
        )

        # --------- sections ----------
        section_total = pn.Column(
            pn.pane.Markdown(
                "### 1. Total CO₂ over time\n"
                "_Top panel: absolute average total CO₂ emissions per country in each group (Mt)._  \n"
                "_Bottom panel: indexed view (first year = 1) so we can compare **relative growth**._"
            ),
            total_abs_plot,
            pn.pane.Markdown(
                "_Indexed growth (first year = 1)_",
            ),
            total_index_plot,
            sizing_mode="stretch_width",
            css_classes=["story-step-card"],
        )

        section_intensity = pn.Column(
            pn.pane.Markdown(
                "### 2. Emission intensity over time\n"
                "_Compare how emission **intensity** (per capita or per GDP) evolves "
                "for the two groups. Use the selector above to switch metric._"
            ),
            intensity_plot,
            sizing_mode="stretch_width",
            css_classes=["story-step-card"],
        )

        section_ratio = pn.Column(
            pn.pane.Markdown(
                "### 3. Top / Bottom CO₂ ratio\n"
                "_How many times higher are emissions in the Top 10 group compared to "
                "the Bottom 10 group? Values above 1 mean Top 10 emits more._"
            ),
            ratio_plot,
            sizing_mode="stretch_width",
            css_classes=["story-step-card"],
        )

        self._layout = pn.Column(
            header,
            controls_row,
            section_total,
            section_intensity,
            section_ratio,
            sizing_mode="stretch_both",
            css_classes=["story-layout"],
        )

    # ------------------------------------------------------------------
    # plotting helpers
    # ------------------------------------------------------------------
    def _total_co2_plot(self):
        """Absolute total CO₂ (Mt) for Top 10 / Bottom 10."""
        df = self.data

        curves = [
            df.hvplot.line(
                x="year",
                y="co2_top10",
                label="Top 10 – total CO₂",
                line_width=2,
            ),
            df.hvplot.line(
                x="year",
                y="co2_bottom10",
                label="Bottom 10 – total CO₂",
                line_width=2,
                line_dash="dotted",
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
            shared_axes=False,   # 👈 ikke del zoom med andre
            framewise=True,
        )

    def _total_co2_index_plot(self):
        """Indexed total CO₂ (first year = 1) to compare relative growth."""
        df = self.data

        curves = [
            df.hvplot.line(
                x="year",
                y="co2_top10_index",
                label="Top 10 – indexed CO₂",
                line_width=2,
            ),
            df.hvplot.line(
                x="year",
                y="co2_bottom10_index",
                label="Bottom 10 – indexed CO₂",
                line_width=2,
                line_dash="dotted",
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


    def _intensity_plot(self, metric: str):
        """CO₂ intensity (per capita or per GDP)."""
        df = self.data

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
            ),
            df.hvplot.line(
                x="year",
                y=y_bottom,
                label=f"Bottom 10{label_suffix}",
                line_width=2,
                line_dash="dotted",
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

    def _ratio_plot(self):
        """Ratio Top/Bottom for total CO₂."""
        df = self.data

        ratio_plot = df.hvplot.line(
            x="year",
            y="co2_ratio_top_over_bottom",
            label="Top / Bottom total CO₂",
            line_width=2,
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


    # ------------------------------------------------------------------
    # Panel integration
    # ------------------------------------------------------------------
    def view(self):
        """Backward-compatible method if someone calls .view()."""
        return self._layout

    @property
    def layout(self):
        """Property used by controllers/templates that expect .layout."""
        return self._layout

    def __panel__(self):
        """
        Make this class directly usable in Panel layouts:
        pn.Column(ShippingStoryboardView(...), ...)
        """
        return self._layout
