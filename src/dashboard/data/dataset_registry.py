# src/dashboard/data/dataset_registry.py
from typing import Dict, Callable
from .data_loader import Dataset
import threading


class DatasetRegistry:
    """
    Keeps track of loaded datasets and notifies callbacks on change.
    Callbacks receive the current dict of datasets (name -> Dataset).
    """
    def __init__(self):
        self._datasets: Dict[str, Dataset] = {}
        self._callbacks: list[Callable[[Dict[str, Dataset]], None]] = []
        self._lock = threading.RLock()

    @property
    def datasets(self) -> Dict[str, Dataset]:
        with self._lock:
            return dict(self._datasets)

    def add(self, dataset: Dataset):
        with self._lock:
            # if name collision, add suffix
            base = dataset.name
            name = base
            i = 1
            while name in self._datasets:
                name = f"{base}_{i}"
                i += 1
            dataset.name = name
            dataset.id = name
            self._datasets[name] = dataset
        self._notify()

    def remove(self, name: str):
        with self._lock:
            if name in self._datasets:
                del self._datasets[name]
        self._notify()

    def get(self, name: str) -> Dataset | None:
        return self._datasets.get(name)

    def on_change(self, callback: Callable[[Dict[str, Dataset]], None]):
        self._callbacks.append(callback)

    def _notify(self):
        for cb in self._callbacks:
            try:
                cb(self.datasets)
            except Exception:
                # avoid letting one bad callback break registry updates
                pass
