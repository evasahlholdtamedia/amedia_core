## This script contain general utility functions useful in any project.
## It is called in nb_import.py, no need for additional imports.

import os
import re
import pandas as pd
from core.get_client import get_client, BILLING_PROJECT
from google.api_core import exceptions
from pathlib import Path

def run_sql(query: str, billing_project: str = BILLING_PROJECT):
    '''Query GCP and return a dataframe. 
    Args:
        query: SQL query
        billing_project: Custom billing project; defaults to "amedia-analytics-eu"
    '''
    client = get_client(billing_project)
    print("Running query...")
    return client.query(query).to_dataframe()

def save(df, filename):
    """Saves a DataFrame as a CSV in the 'data' folder within the CWD.
    Args:
        df (pd.DataFrame): The DataFrame to export.
        filename (str): The desired name of the file.
    """
    target_dir = os.path.join(os.getcwd(), "data")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    if filename.endswith(".csv"):
        pass
    else:
        filename = f"{filename}.csv"
    export_path = os.path.join(target_dir, filename)
    df.to_csv(export_path, index=False)

def save_xlsx(df, filename):
    """Save a DataFrame as .xlsx with frozen header panes in the 'data' folder
    within the current working directory.
    """
    df_export = df.copy()

    for col in df_export.columns:
        if pd.api.types.is_datetime64_any_dtype(df_export[col]) or df_export[col].dtype == "object":
            try:
                df_export[col] = pd.to_datetime(df_export[col]).dt.tz_localize(None).dt.date
            except (ValueError, TypeError):
                pass

    target_dir = Path.cwd() / "data"
    target_dir.mkdir(parents=True, exist_ok=True)

    export_path = target_dir / f"{Path(filename).stem}.xlsx"

    with pd.ExcelWriter(export_path, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False)
        writer.sheets["Sheet1"].freeze_panes = "A2"

def save_fig(fig, name, folder=None, dpi=200):
    """Save a plot figure. Default location: data/plots in the current working
    directory (created if it does not exist)."""
    folder = Path.cwd() / "data" / "plots" if folder is None else Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    slug = name.lower().translate(str.maketrans({"æ": "ae", "ø": "o", "å": "a"}))
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    path = folder / f"{slug}.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")

def load(filename, parent_folder=None):
    """Loads a CSV file from the 'data' folder within the CWD.
    Args:
        filename (str): The name of the CSV file to load.
        parent_folder (str): Optional name of a parent folder to search upward for. If provided, looks for 'data' folder inside that parent instead of CWD.
    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    if not filename.endswith(".csv"): filename = f"{filename}.csv"
    if parent_folder:
        base = next((p for p in Path.cwd().parents if p.name == parent_folder), None)
        if base is None: raise FileNotFoundError(f"Parent folder '{parent_folder}' not found in path hierarchy.")
    else:
        base = Path.cwd()
    return pd.read_csv(base / "data" / filename)

def trim_string_columns(df):
    """Trim strings columns in a dataframe.
    """
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].str.strip()
    return df

def clean_columns(df):
    """Lowercase column names, strip whitespace, and collapse whitespace and
    repeated underscores into single underscores."""
    df = df.copy()
    df.columns = [re.sub(r"[\s_]+", "_", c.strip().lower()).strip("_") for c in df.columns]
    return df

def drop_empty(df, axis=1):
    """Drop all-null columns (axis=1) or rows (axis=0)."""
    return df.dropna(axis=axis, how="all")

def blank_to_na(df):
    """Convert empty strings and whitespace-only strings to NaN."""
    df = df.copy()
    for col in df.select_dtypes(include="object"):
        df[col] = df[col].replace(r"^\s*$", pd.NA, regex=True)
    return df

