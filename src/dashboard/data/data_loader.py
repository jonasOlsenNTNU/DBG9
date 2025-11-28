# src/dashboard/data/data_loader.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any
import pandas as pd


@dataclass
class Dataset:
    """Simple dataset container."""
    id: str                # unique id (could be name or uuid)
    name: str              # human-friendly name
    path: Path | None      # path if loaded from disk
    df: pd.DataFrame
    dtypes: Dict[str, str]

    @property
    def columns(self):
        return list(self.df.columns)

    @property
    def row_count(self) -> int:
        return len(self.df)

    @property
    def preview(self) -> pd.DataFrame:
        return self.df.head(10)


def load_csv(path: str, dataset_id: str | None = None) -> Dataset:
    """
    Load CSV into Dataset. `path` can be filesystem path.
    Returns Dataset object.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise ValueError(f"CSV file not found: {path}")

    df = pd.read_csv(path_obj)
    name = path_obj.stem
    if dataset_id is None:
        dataset_id = name
    return Dataset(id=dataset_id, name=name, path=path_obj, df=df, dtypes={c: str(t) for c, t in df.dtypes.items()})
