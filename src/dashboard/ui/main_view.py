# src/dashboard/ui/main_view.py
import panel as pn
from .sidebar_view import SidebarView
from .dataset_view import DatasetView
from .panel_creation_dialog import PanelCreationDialog

pn.extension('tabulator')

class MainView:
    def __init__(self, registry=None):
        self.sidebar = SidebarView()
        self.dataset_view = DatasetView()
        self.panels_area = pn.Column(sizing_mode="stretch_both")
        self.creation_dialog = PanelCreationDialog(registry)

        header = pn.pane.Markdown("# Data Dashboard", sizing_mode="stretch_width")

        main_area = pn.Column(
            header,
            pn.layout.Divider(),
            self.dataset_view.view(),
            pn.pane.Markdown("## 📊 Panels"),
            self.panels_area,
            self.creation_dialog.dialog,
            sizing_mode="stretch_both",
        )

        self._layout = pn.Row(self.sidebar.view(), pn.layout.Spacer(width=10), main_area, sizing_mode="stretch_both")

    def add_panel(self, panel_view):
        self.panels_area.append(panel_view.layout)

    def remove_panel(self, panel_view):
        try:
            self.panels_area.objects.remove(panel_view.layout)
        except ValueError:
            pass

    def view(self):
        return self._layout
