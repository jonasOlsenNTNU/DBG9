# src/dashboard/ui/panel_creation_dialog.py
import panel as pn

class PanelCreationDialog:
    """
    Modal-like widget to create new panels.
    Exposes `on_submit(callback(config_dict))`.
    """
    def __init__(self, registry):
        self.registry = registry
        self._submit_cbs = []

        self.dataset_multiselect = pn.widgets.MultiSelect(
            name="Select dataset(s)", options=list(self.registry.datasets.keys()), size=4
        )
        self.plot_type_select = pn.widgets.Select(name="Plot type", options=["scatter", "line", "bar"])
        self.x_col_select = pn.widgets.Select(name="X axis")
        self.y_col_select = pn.widgets.Select(name="Y axis")

        self.create_button = pn.widgets.Button(name="Create", button_type="success")
        self.cancel_button = pn.widgets.Button(name="Cancel", button_type="default")
        
        self.create_button.on_click(self._handle_create)
        self.cancel_button.on_click(self._handle_cancel)
        self.dataset_multiselect.param.watch(self._update_column_options, "value")

        self.dialog = pn.Card(
            pn.Column(
                pn.pane.Markdown("## Create new panel"),
                self.dataset_multiselect,
                self.plot_type_select,
                self.x_col_select,
                self.y_col_select,
                pn.Row(self.create_button, self.cancel_button),
            ),
            visible=False,
            sizing_mode="stretch_width",
            margin=10,
        )

    # ---------------------------------------------------
    def _update_column_options(self, event):
        selected = event.new
        if not selected:
            self.x_col_select.options = []
            self.y_col_select.options = []
            return
        # for simplicity, use columns of first dataset for now
        first = self.registry.get(selected[0])
        if first:
            self.x_col_select.options = first.columns
            self.y_col_select.options = first.columns

    # ---------------------------------------------------
    def _handle_create(self, _):
        if not self.dataset_multiselect.value:
            return
        cfg = {
            "title": f"Panel ({', '.join(self.dataset_multiselect.value)})",
            "sources": list(self.dataset_multiselect.value),
            "plot_type": self.plot_type_select.value,
            "x": self.x_col_select.value,
            "y": self.y_col_select.value,
        }
        for cb in self._submit_cbs:
            cb(cfg)
        self.dialog.visible = False

    def _handle_cancel(self, _):
        self.dialog.visible = False

    def on_submit(self, cb):
        self._submit_cbs.append(cb)

    def open(self):
        self.dataset_multiselect.options = list(self.registry.datasets.keys())
        self.dialog.visible = True
