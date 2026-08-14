## This script contain general utility functions useful in any project.
## It is called in nb_import.py, no need for additional imports.

import os
import re
import pandas as pd
from core.get_client import get_client, BILLING_PROJECT
from google.api_core import exceptions
from pathlib import Path

## TO BE ADDED: 

# Function for grid control 

# "Skeleton" for SQL queries

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


def _clean_columns(df):
    """Normalise column names: lowercase, strip, collapse whitespace and
    repeated underscores. Handles non-string names, MultiIndex and duplicates."""
    df = df.copy()

    def clean(name):
        if isinstance(name, tuple):
            parts = [clean(p) for p in name if p is not None]
            return "_".join(p for p in parts if p) or "column"
        text = re.sub(r"[\s_]+", "_", str(name).strip().lower()).strip("_")
        return text or "column"

    seen, names = {}, []
    for raw in df.columns:
        name = clean(raw)
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        names.append(name)

    df.columns = names
    return df

def _trim_strings(df):
    """Strip leading and trailing whitespace from string values."""
    df = df.copy()
    for i, dtype in enumerate(df.dtypes):
        s = df.iloc[:, i]
        if isinstance(dtype, pd.StringDtype):
            df.isetitem(i, s.str.strip())
        elif dtype == object:
            df.isetitem(i, s.map(lambda x: x.strip() if isinstance(x, str) else x))
    return df

def _blank_to_na(df):
    """Convert empty and whitespace-only strings to NA."""
    df = df.copy()
    for i, dtype in enumerate(df.dtypes):
        if not (dtype == object or isinstance(dtype, pd.StringDtype)):
            continue
        s = df.iloc[:, i]
        blank = s.map(lambda x: isinstance(x, str) and x.strip() == "")
        blank = blank.fillna(False).astype(bool)
        if blank.any():
            df.isetitem(i, s.mask(blank, pd.NA))
    return df

def _drop_empty(df, axis=1):
    """Drop all-null columns (axis=1) or rows (axis=0)."""
    if df.shape[1 - axis] == 0:
        return df.copy()
    return df.dropna(axis=axis, how="all")

def _round_numerics(df, decimals):
    """Round float columns to a given number of decimals."""
    df = df.copy()
    if decimals is None:
        return df
    for i, dtype in enumerate(df.dtypes):
        if pd.api.types.is_float_dtype(dtype):
            df.isetitem(i, df.iloc[:, i].round(decimals))
    return df

def format_dataframe(df, decimals=2):
    """Format a pd.DataFrame to custom standards:
    - Clean column names
    - Trim strings and convert blanks to NA
    - Drop all-null columns
    - Round float columns: default 2 decimals
    """
    df = _clean_columns(df)
    df = _trim_strings(df)
    df = _blank_to_na(df)
    df = _drop_empty(df)
    df = _round_numerics(df, decimals)
    return df

_unit_scale = {
    None: (1, None),
    "tusen": (1e3, "tusen"),
    "T": (1e3, "tusinn"),
    "1000": (1e3, "tusinn"),
    "mill": (1e6, "M"),
    "M": (1e6, "M"),
    "mil": (1e6, "M"),
    "million": (1e6, "M"),
    "millioner": (1e6, "M"),
    "1000000": (1e6, "M"),
}

def format_numbers(value, scale=None, decimals=2, unit=None):
    '''
    Format a number using Norwegian conventions: space as thousands separator
    and comma as decimal separator.

    Args:
        value (float | int): The number to format.
        scale (str, optional): Scale to divide by. 
            None (default) leaves the value unscaled.
        decimals (int): Number of decimals. Defaults to 2.
        unit (str, optional): String appended after the number, e.g. 'kr'
            or '%'. Defaults to None (nothing appended).

    Returns:
        str: The formatted number, e.g. set_value(1234567.8, 'mill', 1, 'kr')
            returns '1,2 mill. kr'.
    '''
    if scale not in _unit_scale:
        valid = ", ".join(repr(k) for k in _unit_scale)
        raise ValueError(f"unit must be one of {valid}, got {scale!r}")

    if value is None or pd.isna(value):
        return "–"

    divisor, scale_label = _unit_scale[scale]
    text = f"{value / divisor:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")

    parts = [text]
    if scale_label:
        parts.append(scale_label)
    if unit:
        parts.append(unit)

    return "\u00a0".join(parts)