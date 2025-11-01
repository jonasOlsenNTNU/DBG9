# src/dashboard/ui/sidebar_view.py
import panel as pn
import pandas as pd
from ..utils.load_css import load_css

pn.extension('tabulator')

class SidebarView:
    """
    Sidebar view that exposes event hooks:
      - on_upload(callback(file_bytes, filename))
      - on_select(callback(dataset_name))
      - on_remove(callback(dataset_name))
    Also provides update_dataset_list(datasets_dict) to refresh options.
    """
    def __init__(self):
        load_css("sidebar_view.css")

        # Create objects to put in panel (widgets)
        self.file_input = pn.widgets.FileInput(accept=".csv", multiple=False)
        self.dataset_select = pn.widgets.Select(name="Loaded datasets", options=[])
        self.remove_button = pn.widgets.Button(name="Remove dataset", button_type="warning", disabled=True)
        self.new_panel_button = pn.widgets.Button(name="New Panel", button_type="primary")

        # Apply CSS to widgets
        self.file_input.css_classes = ["sidebar-file-input"]
        self.dataset_select.css_classes = ["sidebar-dataset-select"]
        self.remove_button.css_classes = ["sidebar-remove-button"]
        self.new_panel_button.css_classes = ["sidebar-new-panel-button"]

        # internal callback holders
        self._upload_cbs = []
        self._select_cbs = []
        self._remove_cbs = []
        self._new_panel_cbs = []

        # Wire widget events to anonymous handlers that dispatch to registered callbacks
        self.file_input.param.watch(self._handle_upload, "value")
        self.dataset_select.param.watch(self._handle_select, "value")
        self.remove_button.on_click(self._handle_remove)
        self.new_panel_button.on_click(self._handle_new_panel)

        # Create SidebarView Panel
        self._panel = pn.Column(
            pn.pane.Markdown("## 📁 Datasets", css_classes=["sidebar-header"]),
            self.file_input,
            pn.pane.Markdown("### Available", css_classes=["sidebar-subheader"]),
            self.dataset_select,
            self.remove_button,
            pn.layout.Divider(),
            self.new_panel_button,
            sizing_mode="stretch_width",
            css_classes=["sidebar-container"],
        )

    # -------------------------
    # Hooks registration
    # -------------------------
    def on_upload(self, cb):
        self._upload_cbs.append(cb)

    def on_select(self, cb):
        self._select_cbs.append(cb)

    def on_remove(self, cb):
        self._remove_cbs.append(cb)

    def on_new_panel(self, cb):
        self._new_panel_cbs.append(cb)

    # -------------------------
    # Internal handlers
    # -------------------------
    def _handle_upload(self, event):
        if not event.new:
            return
        # event.new is raw bytes of the uploaded file
        filename = getattr(self.file_input, "filename", None)
        for cb in self._upload_cbs:
            try:
                cb(event.new, filename)
            except Exception:
                pass
        # clear file input widget value so same filename can be uploaded again if desired
        self.file_input.value = None

    def _handle_select(self, event):
        # event.new is selected name
        name = event.new
        self.remove_button.disabled = False if name else True
        for cb in self._select_cbs:
            try:
                cb(name)
            except Exception:
                pass

    def _handle_remove(self, _):
        name = self.dataset_select.value
        for cb in self._remove_cbs:
            try:
                cb(name)
            except Exception:
                pass

    def _handle_new_panel(self, _):
        for cb in self._new_panel_cbs:
            try:
                cb()
            except Exception:
                pass

    # -------------------------
    # Public update method
    # -------------------------
    def update_dataset_list(self, datasets: dict):
        options = list(datasets.keys())
        self.dataset_select.options = options
        if not options:
            self.dataset_select.value = None
            self.remove_button.disabled = True
        else:
            # keep selection if still present, otherwise pick last
            if self.dataset_select.value not in options:
                self.dataset_select.value = options[-1]

    def view(self):
        return self._panel
