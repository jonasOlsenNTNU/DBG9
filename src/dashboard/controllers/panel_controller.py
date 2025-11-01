# src/dashboard/controllers/panel_controller.py
import hvplot.pandas  # noqa
from ..data.dataset_registry import DatasetRegistry
from ..ui.panel_view import PanelView

class PanelController:
    """Handles a single user-created panel (plot)."""
    _counter = 0

    def __init__(self, registry: DatasetRegistry, config: dict, remove_callback):
        PanelController._counter += 1
        self.id = f"panel_{PanelController._counter}"
        self.registry = registry
        self.config = config
        self.remove_callback = remove_callback
        self.view = PanelView(self.id, self.config["title"])
        self._render_plot()
        self.view.on_close(self._handle_close)

    # ---------------------------------------------------
    def _render_plot(self):
        sources = self.config["sources"]
        plot_type = self.config["plot_type"]
        x = self.config["x"]
        y = self.config["y"]

        if not sources:
            self.view.show_message("No data source selected.")
            return

        # For now, single-source plots only. Multi-source support later.
        ds = self.registry.get(sources[0])
        if ds is None:
            self.view.show_message("Dataset not found.")
            return

        df = ds.df
        if x not in df.columns or y not in df.columns:
            self.view.show_message("Selected columns not found.")
            return

        hvplot_func = getattr(df.hvplot, plot_type)
        plot = hvplot_func(x=x, y=y, height=350, width=600, title=f"{ds.name}: {x} vs {y}")
        self.view.update_plot(plot)

    # ---------------------------------------------------
    def _handle_close(self):
        self.remove_callback(self)
