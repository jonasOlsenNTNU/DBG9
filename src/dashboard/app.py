import sys
import argparse
import panel as pn
from .controllers.shipping_controller import ShippingDashboardController
from .utils.load_css import load_css


def load_resources():
    pn.extension("tabulator")
    load_css("global.css")
    load_css("oecd_theme.css")


def rebuild_dataset():
    """Rebuild the analysis dataset from source data."""
    print("Rebuilding analysis dataset...")
    print("This may take 30-60 seconds...\n")
    
    # Import here to avoid slow imports on normal startup
    from ..utils.data.data_pipeline import build_analysis_dataset, save_analysis_dataset
    
    df = build_analysis_dataset()
    save_analysis_dataset(df)
    
    print("\n✅ Dataset rebuild complete!")
    print("   You can now run the dashboard normally.")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Maritime Emissions Analysis Dashboard"
    )
    parser.add_argument(
        '--rebuild-dataset',
        action='store_true',
        help='Rebuild analysis dataset from source data (expensive operation)'
    )
    
    args = parser.parse_args()
    
    # Handle dataset rebuild
    if args.rebuild_dataset:
        rebuild_dataset()
        return
    
    # Normal dashboard startup
    load_resources()
    controller = ShippingDashboardController()
    pn.serve(
        controller.layout,
        title="Shipping & CO₂ Dashboard",
        show=True,
    )


if __name__ == "__main__":
    main()
