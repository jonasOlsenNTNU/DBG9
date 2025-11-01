# src/dashboard/ui/main_view.py
import panel as pn
from .sidebar_view import SidebarView
from .dataset_view import DatasetView
from .panel_creation_dialog import PanelCreationDialog
from ..utils.load_css import load_css

pn.extension('tabulator')

class MainView:
    def __init__(self, registry=None):
        load_css("main_view.css")

        # Create objects (widgets) to put in panel.
        self.sidebar = SidebarView()
        self.dataset_view = DatasetView()
        self.panels_area = pn.Column(sizing_mode="stretch_width")
        
        # Dialog initially hidden
        self.creation_dialog = PanelCreationDialog(registry)
        self.creation_dialog.dialog.visible = False
        self.creation_dialog.dialog.css_classes.append("floating-dialog")

        #Add CSS for widgets.
        self.sidebar._panel.css_classes.append("main-sidebar")
        self.panels_area.css_classes.append("panels_container")

        header = pn.pane.Markdown("# Data Dashboard", sizing_mode="stretch_width")


        # Scrollable stack
        self.scrollable_stack = pn.Column(
            self.dataset_view.view(),
            pn.pane.Markdown("## 📊 Panels"),
            self.panels_area,
            sizing_mode="stretch_width",
            css_classes=["scrollable-stack"]
        )

        main_area = pn.Column(
            header,
            pn.layout.Divider(),
            self.scrollable_stack,
            self.creation_dialog.dialog,  # Hidden until called
            sizing_mode="stretch_both",
            css_classes=["main-content-area"]
        )

        self._layout = pn.Row(
            self.sidebar.view(), 
            main_area, 
            sizing_mode="stretch_both",
            css_classes=["main-layout"]
            )

    def add_panel(self, panel_view):
        self.panels_area.append(panel_view.layout)

    def remove_panel(self, panel_view):
        try:
            self.panels_area.objects.remove(panel_view.layout)
        except ValueError:
            pass
    
    def view(self):
        return self._layout
