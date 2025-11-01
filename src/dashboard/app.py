# src/dashboard/app.py
import panel as pn
from .controllers.dashboard_controller import DashboardController

def main():
    controller = DashboardController()
    pn.serve(controller.layout, title="Data Dashboard", show=True)

if __name__ == "__main__":
    main()
