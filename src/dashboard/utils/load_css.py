# src/dashboard/utils/load_css.py
import os
import panel as pn

# Prevent duplicate loads
_LOADED_FILES = set()

def load_css(filename: str):
    """
    Loads a CSS file from the dashboard/assets directory into Panel.
    
    Args:
        filename (str): Name of the CSS file (e.g. "global.css" or "sidebar_view.css").
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    css_path = os.path.join(base_dir, filename)

    if not os.path.exists(css_path):
        raise FileNotFoundError(f"CSS file not found: {css_path}")

    if css_path not in _LOADED_FILES:
        with open(css_path, "r") as f:
            css = f.read()
        pn.config.raw_css.append(css)
        _LOADED_FILES.add(css_path)
