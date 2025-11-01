# src/dashboard/ui/main_view.py
import panel as pn
from .sidebar_view import SidebarView
from .dataset_view import DatasetView

pn.extension('tabulator')

class MainView:
    """
    Compose SidebarView and DatasetView into the full app layout.
    Exposes subviews for controller to hook into.
    """
    def __init__(self):
        self.sidebar = SidebarView()
        self.dataset_view = DatasetView()

        header = pn.pane.Markdown("# Data Dashboard", sizing_mode="stretch_width")

        main_area = pn.Column(
            header,
            pn.layout.Divider(),
            self.dataset_view.view(),
            sizing_mode="stretch_both",
        )

        self._layout = pn.Row(self.sidebar.view(), pn.layout.Spacer(width=10), main_area, sizing_mode="stretch_both")

    def view(self):
        return self._layout
