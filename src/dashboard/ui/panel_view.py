# src/dashboard/ui/panel_view.py
import panel as pn
from ..utils.load_css import load_css

class PanelView:
    """Visual container for a single panel plot, with a close button."""
    def __init__(self, panel_id: str, title: str):
        load_css("panel_view.css")

        self.panel_id = panel_id
        self.title = title
        self.close_button = pn.widgets.Button(name="✖", button_type="danger", width=40)
        self.plot_pane = pn.pane.HoloViews(None, sizing_mode="stretch_width")
        self._on_close = []

        header = pn.Row(
            pn.pane.Markdown(f"### {self.title}"),
            pn.layout.Spacer(),
            self.close_button,
            sizing_mode="stretch_width",
        )

        card = pn.Card(header, self.plot_pane, sizing_mode="stretch_width", margin=10)


        # Apply CSS to widgets.
        header.css_classes.append("panel-header")
        card.css_classes.append("panel-card")

        self.layout = pn.Column(
            card,
            sizing_mode="stretch_width"
        )

        self.close_button.on_click(lambda _: self._trigger_close())

    # --------------------------------
    def on_close(self, callback):
        self._on_close.append(callback)

    def _trigger_close(self):
        for cb in self._on_close:
            cb()

    def update_plot(self, plot_obj):
        self.plot_pane.object = plot_obj

    def show_message(self, msg: str):
        self.plot_pane.object = pn.pane.Markdown(f"_{msg}_")
