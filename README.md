# DBG9
Project repo for Group 9 - IE500417 2025 Høst


## Install Dependencies

Dependencies are defined in the pyproject.toml file.
Run ' pip install . ' from project directory (Powershell/Bash)


Run the app using CLI command:

python -m src.dashboard.app

## Adding new data 

Place data files in /data folder.

## Updating analysis_ready.csv

When updating the data tables run the app with the flag: "--rebuild-dataset" 

More documentation about this process in: src/utils/data/README.md

## Data Sources

OECD:

https://data-explorer.oecd.org/vis?fs[0]=Topic%2C1%7CEnvironment%20and%20climate%20change%23ENV%23%7CAir%20and%20climate%23ENV_AC%23&pg=0&fc=Topic&bp=true&snb=15&df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_MARITIME_TRANSPORT%40DF_MARITIME_TRANSPORT&df[ag]=OECD.SDD.NAD.SEEA&df[vs]=&dq=.M........&pd=2022-01%2C&to[TIME_PERIOD]=false

OWID:

https://github.com/owid/co2-data?tab=readme-ov-file

