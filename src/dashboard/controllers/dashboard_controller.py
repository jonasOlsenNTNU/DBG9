# src/dashboard/controllers/dashboard_controller.py
from ..data.dataset_registry import DatasetRegistry
from ..data.data_loader import load_csv
from ..ui.main_view import MainView
from .panel_controller import PanelController
import tempfile, os

class DashboardController:
    def __init__(self):
        self.registry = DatasetRegistry()
        self.view = MainView(self.registry)
        self.panel_controllers = []

        # Wire registry and sidebar events
        self.registry.on_change(self.view.sidebar.update_dataset_list)
        self.view.sidebar.on_upload(self.handle_upload)
        self.view.sidebar.on_select(self.handle_select)
        self.view.sidebar.on_remove(self.handle_remove)
        self.view.sidebar.on_new_panel(self.handle_new_panel)

        # Wire panel creation dialog
        self.view.creation_dialog.on_submit(self.handle_panel_created)

    # ---------------------------------------------------
    def handle_upload(self, file_bytes, filename):
        if not file_bytes or not filename:
            return
        tmpfile = os.path.join(tempfile.gettempdir(), filename)
        with open(tmpfile, "wb") as f:
            f.write(file_bytes)
        ds = load_csv(tmpfile)
        self.registry.add(ds)

    def handle_select(self, dataset_name):
        ds = self.registry.get(dataset_name)
        if ds:
            self.view.dataset_view.render_dataset(ds)
        else:
            self.view.dataset_view.clear()

    def handle_remove(self, dataset_name):
        self.registry.remove(dataset_name)
        self.view.dataset_view.clear()

    # ---------------------- Panels ---------------------
    def handle_new_panel(self):
        self.view.creation_dialog.open()

    def handle_panel_created(self, config):
        ctrl = PanelController(self.registry, config, remove_callback=self.remove_panel)
        self.panel_controllers.append(ctrl)
        self.view.add_panel(ctrl.view)

    def remove_panel(self, panel_ctrl):
        self.panel_controllers.remove(panel_ctrl)
        self.view.remove_panel(panel_ctrl.view)

    # ---------------------------------------------------
    def layout(self):
        return self.view.view()
