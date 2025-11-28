# src/dashboard/app.py
import panel as pn
from .controllers.shipping_controller import ShippingDashboardController
from .utils.load_css import load_css


def load_resources():
    """
    Load Panel resources and css.
    """
    pn.extension('tabulator')
    load_css("global.css")


def main():
    load_resources()
    controller = ShippingDashboardController()
    pn.serve(
        controller.layout,           # function that returns the root layout
        title="Shipping & CO₂ Dashboard",
        show=True
    )


if __name__ == "__main__":
    main()
