# src/dashboard/app.py
import panel as pn
from .controllers.dashboard_controller import DashboardController
from .utils.load_css import load_css

def load_resources():
    """
    Load Panel resources and css.
    """
    pn.extension('tabulator')
    load_css("global.css")



def main():
    load_resources()
    controller = DashboardController()
    pn.serve(controller.layout, title="Data Dashboard", show=True)

if __name__ == "__main__":
    main()

