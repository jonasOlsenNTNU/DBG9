# src/dashboard/controllers/dashboard_controller.py
from ..data.dataset_registry import DatasetRegistry
from ..data.data_loader import load_csv, Dataset
from ..ui.main_view import MainView
import tempfile, os

class DashboardController:
    """
    Orchestrates DatasetRegistry and Views.
    """
    def __init__(self):
        self.registry = DatasetRegistry()
        self.view = MainView()

        # wire registry -> view
        self.registry.on_change(self.view.sidebar.update_dataset_list)

        # wire view events -> controller handlers
        self.view.sidebar.on_upload(self.handle_upload)
        self.view.sidebar.on_select(self.handle_select)
        self.view.sidebar.on_remove(self.handle_remove)
        self.view.sidebar.on_new_panel(self.handle_new_panel)  # placeholder for next milestone

    # ---------------------------
    # Event handlers
    # ---------------------------
    def handle_upload(self, file_bytes: bytes, filename: str):
        """
        Save uploaded bytes to temp file and load dataset via load_csv.
        """
        if file_bytes is None or filename is None:
            return
        tmpdir = tempfile.gettempdir()
        safe_path = os.path.join(tmpdir, filename)
        with open(safe_path, "wb") as f:
            f.write(file_bytes)
        ds = load_csv(safe_path)
        # add to registry (registry will notify views)
        self.registry.add(ds)

    def handle_select(self, dataset_name: str):
        if not dataset_name:
            self.view.dataset_view.clear()
            return
        ds = self.registry.get(dataset_name)
        self.view.dataset_view.render_dataset(ds)

    def handle_remove(self, dataset_name: str):
        if not dataset_name:
            return
        self.registry.remove(dataset_name)
        # if removed dataset was displayed, clear inspector
        self.view.dataset_view.clear()

    def handle_new_panel(self):
        # Placeholder: will open creation dialog and create a PanelController
        pass

    # ---------------------------
    # Public helpers
    # ---------------------------
    def layout(self):
        return self.view.view()
