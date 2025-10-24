import pandas as pd
from pathlib import Path

#Path to the data folder
DATA_PATH = Path(__file__).resolve().parents[2] / "data"

#Read data from CSV-file and return a dataframe.
def load_data(filename = "owid-co2-data.csv"):
    file_path = DATA_PATH / filename

    if not file_path.exists():
        raise FileNotFoundError("Data file not found.")
    
    return pd.read_csv(file_path)
