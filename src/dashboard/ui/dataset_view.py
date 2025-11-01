# src/dashboard/ui/dataset_view.py
import panel as pn
import pandas as pd
import hvplot.pandas  # noqa
from ..data.data_loader import Dataset

pn.extension('tabulator')

class DatasetView:
    """Displays metadata, preview, and a quick plot for a single dataset."""

    def __init__(self):
        self.info = pn.pane.Markdown("", sizing_mode="stretch_width")
        self.preview = pn.widgets.Tabulator(pd.DataFrame())
        self.plot_pane = pn.pane.HoloViews(None, sizing_mode="stretch_both")

        self._panel = pn.Column(
            pn.pane.Markdown("## Dataset inspector"),
            self.info,
            self.preview,
            self.plot_pane,
            sizing_mode="stretch_both",
        )

    def render_dataset(self, dataset: Dataset):
        if dataset is None:
            self.clear()
            return
        md = f"""
        ### {dataset.name}
        **Rows:** {dataset.row_count:,}  
        **Columns:** {len(dataset.columns)}  
        **Column names:** {', '.join(dataset.columns[:10])}{'...' if len(dataset.columns)>10 else ''}
        """
        self.info.object = md
        self.preview.value = dataset.preview

        # Quick plot if ≥2 numeric columns
        numeric_cols = dataset.df.select_dtypes(include="number").columns
        if len(numeric_cols) >= 2:
            x, y = numeric_cols[:2]
            plot = dataset.df.hvplot.scatter(x, y, height=400, width=700, title=f"{dataset.name}: {x} vs {y}")
            self.plot_pane.object = plot
        else:
            self.plot_pane.object = pn.pane.Markdown("_No numeric columns available for plotting._")

    def clear(self):
        self.info.object = ""
        self.preview.value = pd.DataFrame()
        self.plot_pane.object = None

    def view(self):
        return self._panel
